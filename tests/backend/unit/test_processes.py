"""Exercise ownership of real child trees, including native Windows Job Objects."""

import os
import subprocess
import sys
import time

import pytest
from core.processes import ProcessTree, child_options, instance_lock


@pytest.mark.parametrize("fail_at", ["create", "configure"])
def test_windows_ownership_failure_cleans_up_new_child(monkeypatch, fail_at):
    from types import SimpleNamespace

    import core.processes as processes

    closed = []
    killed = []
    job = SimpleNamespace(Close=lambda: closed.append(True))

    def create(attributes, name):
        assert isinstance(name, str) and name
        if fail_at == "create":
            raise RuntimeError("job creation failed")
        return job

    def configure(*args):
        raise RuntimeError("job configuration failed")

    monkeypatch.setattr(processes, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setitem(sys.modules, "win32api", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "win32con", SimpleNamespace())
    monkeypatch.setitem(
        sys.modules,
        "win32job",
        SimpleNamespace(
            CreateJobObject=create,
            QueryInformationJobObject=configure,
            JobObjectExtendedLimitInformation=9,
        ),
    )
    monkeypatch.setattr(
        processes,
        "subprocess",
        SimpleNamespace(
            run=lambda command, **kwargs: killed.append(command),
        ),
    )
    with pytest.raises(RuntimeError, match="job .* failed"):
        ProcessTree(12345)
    assert killed == [["taskkill", "/PID", "12345", "/T", "/F"]]
    assert closed == ([] if fail_at == "create" else [True])


def is_running(pid):
    if os.name == "nt":
        import win32api
        import win32con
        import win32event

        try:
            handle = win32api.OpenProcess(win32con.SYNCHRONIZE, False, pid)
        except Exception:
            return False
        try:
            return win32event.WaitForSingleObject(handle, 0) == win32event.WAIT_TIMEOUT
        finally:
            handle.Close()
    result = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True)
    return result.returncode == 0 and not result.stdout.strip().startswith("Z")


@pytest.mark.parametrize("parent_exits", [False, True])
def test_owned_tree_cleanup_including_descendants(tmp_path, parent_exits):
    record = tmp_path / "child.pid"
    script = """import subprocess, sys, time
from pathlib import Path
sys.stdin.readline()
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
Path(sys.argv[1]).write_text(str(child.pid), encoding='utf-8')
if sys.argv[2] == 'False': time.sleep(60)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(record), str(parent_exits)],
        stdin=subprocess.PIPE,
        **child_options(),
    )
    tree = ProcessTree(process.pid)
    try:
        process.stdin.write(b"start\n")
        process.stdin.flush()
        deadline = time.monotonic() + 15
        while not record.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        child_pid = int(record.read_text(encoding="utf-8"))
        assert is_running(child_pid)
        if parent_exits:
            assert process.wait(timeout=10) == 0
        tree.terminate(force=True)
        process.wait(timeout=10)
        deadline = time.monotonic() + 10
        while is_running(child_pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not is_running(child_pid), "A descendant survived cleanup"
    finally:
        tree.terminate(force=True)
        process.wait(timeout=10)
        process.stdin.close()


def test_second_instance_is_rejected_and_lock_releases(monkeypatch, tmp_path):
    monkeypatch.setenv("AGIS_RUNTIME_DIR", str(tmp_path))
    with instance_lock("platform"):
        with pytest.raises(RuntimeError, match="already running"):
            with instance_lock("platform"):
                pytest.fail("duplicate start accepted")
    with instance_lock("platform"):
        pass


def test_launcher_uses_node_directly_for_paths_with_spaces(monkeypatch, tmp_path):
    import shutil

    import dev

    if not shutil.which("node"):
        pytest.skip("Node is required for the platform launcher")
    root = tmp_path / "project with spaces नमस्ते"
    vite = root / "frontend/node_modules/vite/bin/vite.js"
    vite.parent.mkdir(parents=True)
    vite.write_text(
        "process.stdout.write('ready\\n'); setInterval(() => {}, 1000);", encoding="utf-8"
    )
    monkeypatch.setattr(dev, "ROOT", root)
    process = subprocess.Popen(dev.frontend_command(), stdout=subprocess.PIPE, **child_options())
    tree = ProcessTree(process.pid)
    try:
        assert process.stdout.readline() == b"ready\n"
    finally:
        tree.terminate(force=True)
        process.wait(timeout=10)
        process.stdout.close()


def test_launcher_rejects_occupied_port():
    import socket

    import dev

    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        with pytest.raises(RuntimeError, match="already occupied"):
            dev.check_ports([server.getsockname()[1]])


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX servers reuse TIME_WAIT addresses")
def test_launcher_accepts_port_after_server_closes_connection():
    import socket

    import dev

    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        port = server.getsockname()[1]
        server.listen()
        with socket.create_connection(("127.0.0.1", port)) as client:
            connection, _ = server.accept()
            connection.close()
            assert client.recv(1) == b""
    dev.check_ports([port])


def test_launcher_rejects_invalid_settings_before_starting_children(monkeypatch):
    from unittest.mock import MagicMock

    import dev

    monkeypatch.setenv("DEBUG", "WARN")
    secret = "CHANGE_ME_PRIVATE_VALUE_MUST_NOT_BE_LOGGED"
    monkeypatch.setenv("JWT_SECRET", secret)
    popen = MagicMock()
    monkeypatch.setattr(dev.subprocess, "Popen", popen)
    with pytest.raises(RuntimeError, match="Invalid application settings") as error:
        dev.run_services()
    assert "DEBUG" in str(error.value) and "JWT_SECRET" in str(error.value)
    assert "true or false" in str(error.value)
    assert secret not in str(error.value)
    popen.assert_not_called()


@pytest.mark.parametrize("source", ["dotenv", "shell"])
def test_launcher_routes_worker_and_frontend_to_its_backend(monkeypatch, source):
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from urllib.parse import urlsplit

    import dotenv

    import dev

    stale_url = "http://127.0.0.1:8004"
    monkeypatch.delenv("WORKER_BACKEND_URL", raising=False)
    if source == "shell":
        monkeypatch.setenv("WORKER_BACKEND_URL", stale_url)
    monkeypatch.setenv("VITE_BACKEND_URL", stale_url)
    monkeypatch.setenv("VITE_API_BASE_URL", stale_url + "/api/v1")

    def load_env(*args, **kwargs):
        if source == "dotenv":
            monkeypatch.setenv("WORKER_BACKEND_URL", stale_url)

    monkeypatch.setattr(dotenv, "load_dotenv", load_env)
    monkeypatch.setenv("LM_STUDIO_URL", "")
    monkeypatch.setattr(dev, "frontend_command", lambda: ["node", "vite"])
    monkeypatch.setattr(dev, "check_ports", lambda: None)
    monkeypatch.setattr(dev.uuid, "uuid4", lambda: SimpleNamespace(hex="test-run"))
    process = MagicMock(pid=12345)
    process.poll.return_value = None
    popen = MagicMock(return_value=process)
    monkeypatch.setattr(dev.subprocess, "Popen", popen)
    monkeypatch.setattr(dev, "ProcessTree", MagicMock())
    response = MagicMock(status=200)
    response.read.return_value = b'{"instance_id":"test-run"}'
    connection = MagicMock()
    connection.__enter__.return_value = response
    monkeypatch.setattr(dev.urllib.request, "urlopen", MagicMock(return_value=connection))
    monkeypatch.setattr(dev.time, "sleep", MagicMock(side_effect=KeyboardInterrupt))

    assert dev.run_services() == 0
    backend, worker, frontend = popen.call_args_list
    address = urlsplit(worker.kwargs["env"]["WORKER_BACKEND_URL"])
    command = backend.args[0]
    assert address.hostname == command[command.index("--host") + 1]
    assert address.port == int(command[command.index("--port") + 1])
    assert worker.kwargs["env"]["WORKER_HEALTH_PORT"] == "8009"
    assert frontend.kwargs["env"]["VITE_BACKEND_URL"] == address.geturl()
    assert frontend.kwargs["env"]["VITE_API_BASE_URL"] == "/api/v1"


async def test_native_async_subprocess_pipes_preserve_unicode():
    import asyncio
    import json

    script = "import sys, json; data=json.loads(sys.stdin.buffer.read().decode('utf-8')); sys.stdout.buffer.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))"
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        script,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        **child_options(),
    )
    tree = ProcessTree(process.pid)
    try:
        payload = {"idea": "नमस्ते — café"}
        output, _ = await asyncio.wait_for(
            process.communicate(json.dumps(payload, ensure_ascii=False).encode("utf-8")), 15
        )
        assert process.returncode == 0
        assert json.loads(output.decode("utf-8")) == payload
    finally:
        tree.terminate(force=True)
        await process.wait()
