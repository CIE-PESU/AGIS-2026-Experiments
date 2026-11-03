#!/usr/bin/env python3
"""Start the application with `python dev.py` in the activated root environment.

Start MongoDB/Kafka with Docker Compose first; stop Compose after Ctrl+C.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8008
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
WORKER_HEALTH_PORT = 8009
FRONTEND_PORT = 5167
sys.path.insert(0, str(ROOT / "backend"))
from core.processes import ProcessTree, child_options, instance_lock


def frontend_command() -> list[str]:
    node = shutil.which("node")
    vite = ROOT / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
    if not node or not vite.is_file():
        raise RuntimeError("Install Node 22.13+ and run npm ci --prefix frontend first.")
    # Avoid npm.cmd / shell quoting differences on Windows and paths with spaces.
    return [node, str(vite), "--host", BACKEND_HOST, "--port", str(FRONTEND_PORT), "--strictPort"]


def check_ports(ports=(BACKEND_PORT, WORKER_HEALTH_PORT, FRONTEND_PORT)) -> None:
    for port in ports:
        with socket.socket() as listener:
            # Match asyncio's POSIX server sockets: recently closed connections
            # in TIME_WAIT must not block an immediate restart. Windows address
            # reuse can share a live listener, so keep its normal bind check.
            if sys.platform != "win32":
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                listener.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(
                    f"Port {port} is already occupied. Stop the existing instance before starting AGIS."
                ) from exc


def run_services() -> int:
    from core.llm_provider import check_model_server, is_local_endpoint
    from dotenv import load_dotenv
    from pydantic import ValidationError

    load_dotenv(ROOT / ".env", encoding="utf-8")
    try:
        from core.config import Settings

        config = Settings()
    except ValidationError as exc:
        # Report field names without echoing credential values from validation errors.
        fields = sorted({".".join(map(str, error["loc"])) for error in exc.errors()})
        hint = " DEBUG must be true or false." if "DEBUG" in fields else ""
        raise RuntimeError(
            f"Invalid application settings: {', '.join(fields)}."
            f" Check .env and shell overrides.{hint}"
        ) from None
    if is_local_endpoint(config.LM_STUDIO_URL):
        check_model_server(config.LM_STUDIO_URL, config.OPENAI_MODEL_NAME, config.OPENAI_API_KEY)
    command = frontend_command()
    check_ports()
    processes = []
    run_id = uuid.uuid4().hex

    def start(arguments, cwd, extra=None):
        env = {
            **os.environ,
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "AGIS_RUN_ID": run_id,
            **(extra or {}),
        }
        process = subprocess.Popen(arguments, cwd=cwd, env=env, **child_options())
        processes.append((process, None))
        tree = ProcessTree(process.pid)
        processes[-1] = (process, tree)
        return process

    def wait_ready(url, timeout=120, *, check_instance=False):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(p.poll() is not None for p, _ in processes):
                raise RuntimeError("A service exited during startup; inspect its output above.")
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        if check_instance and json.load(response).get("instance_id") != run_id:
                            raise RuntimeError(
                                "Readiness responded from a different AGIS instance; startup stopped."
                            )
                        return
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.25)
        raise RuntimeError(f"Service did not become ready: {url}")

    def stop(*_):
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, stop)
    try:
        start(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                BACKEND_HOST,
                "--port",
                str(BACKEND_PORT),
            ],
            ROOT / "backend",
        )
        wait_ready(f"{BACKEND_URL}/api/v1/ready", check_instance=True)
        start(
            [sys.executable, "-m", "workers.combined_agent_worker"],
            ROOT / "backend",
            # This launcher owns the backend address; stale .env/shell values
            # must not redirect persisted callbacks to another port or host.
            {"WORKER_HEALTH_PORT": str(WORKER_HEALTH_PORT), "WORKER_BACKEND_URL": BACKEND_URL},
        )
        wait_ready(f"http://{BACKEND_HOST}:{WORKER_HEALTH_PORT}/health", check_instance=True)
        start(
            command,
            ROOT / "frontend",
            {"VITE_BACKEND_URL": BACKEND_URL, "VITE_API_BASE_URL": "/api/v1"},
        )
        wait_ready(f"http://{BACKEND_HOST}:{FRONTEND_PORT}")
        print(
            f"AGIS ready: http://localhost:{FRONTEND_PORT} (Ctrl+C stops all services)", flush=True
        )
        while all(p.poll() is None for p, _ in processes):
            time.sleep(0.5)
        raise RuntimeError("A service stopped unexpectedly.")
    except KeyboardInterrupt:
        return 0
    finally:
        signal.signal(signal.SIGTERM, previous)
        for process, tree in reversed(processes):
            if tree is not None:
                tree.terminate()
            elif process.poll() is None:
                process.kill()
        for process, tree in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if tree is not None:
                    tree.terminate(force=True)
                process.kill()
                process.wait()
            finally:
                # Also remove descendants left after a parent exits normally.
                if tree is not None:
                    tree.terminate(force=True)


def main() -> int:
    try:
        with instance_lock("platform"):
            return run_services()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
