"""Exercise ownership of real child trees, including native Windows Job Objects."""
import os
import subprocess
import sys
import time

import pytest

from core.processes import ProcessTree, child_options, instance_lock


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
    script = '''import subprocess, sys, time
from pathlib import Path
sys.stdin.readline()
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
Path(sys.argv[1]).write_text(str(child.pid), encoding='utf-8')
if sys.argv[2] == 'False': time.sleep(60)
'''
    process = subprocess.Popen([sys.executable, "-c", script, str(record), str(parent_exits)], stdin=subprocess.PIPE, **child_options())
    tree = ProcessTree(process.pid)
    try:
        process.stdin.write(b"start\n")
        process.stdin.flush()
        deadline = time.monotonic() + 15
        while not record.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        child_pid = int(record.read_text(encoding="utf-8"))
        assert is_running(child_pid)
        if parent_exits:
            assert process.wait(timeout=10) == 0
        tree.terminate(force=True)
        process.wait(timeout=10)
        deadline = time.monotonic() + 10
        while is_running(child_pid) and time.monotonic() < deadline:
            time.sleep(.02)
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
    vite.write_text("process.stdout.write('ready\\n'); setInterval(() => {}, 1000);", encoding="utf-8")
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


async def test_native_async_subprocess_pipes_preserve_unicode():
    import asyncio
    import json
    script = "import sys, json; data=json.loads(sys.stdin.buffer.read().decode('utf-8')); sys.stdout.buffer.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))"
    process = await asyncio.create_subprocess_exec(sys.executable, "-c", script,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, **child_options())
    tree = ProcessTree(process.pid)
    try:
        payload = {"idea": "नमस्ते — café"}
        output, _ = await asyncio.wait_for(process.communicate(json.dumps(payload, ensure_ascii=False).encode('utf-8')), 15)
        assert process.returncode == 0
        assert json.loads(output.decode('utf-8')) == payload
    finally:
        tree.terminate(force=True)
        await process.wait()
