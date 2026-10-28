#!/usr/bin/env python3
"""Run with `python dev.py` using the project virtual environment; stop all services on failure or Ctrl+C."""
from __future__ import annotations
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
LOCAL_ENV = {"WORKER_BACKEND_URL": "http://127.0.0.1:8004", "VITE_BACKEND_URL": "http://127.0.0.1:8004"}


def main() -> int:
    processes: list[subprocess.Popen] = []
    worker_ready_file = ROOT / ".crewai_storage" / f".worker-ready-{os.getpid()}"
    notification_ready_file = ROOT / ".crewai_storage" / f".notification-ready-{os.getpid()}"
    worker_ready_file.parent.mkdir(parents=True, exist_ok=True)
    worker_ready_file.unlink(missing_ok=True)
    notification_ready_file.unlink(missing_ok=True)

    def ensure_port_available(port):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                raise RuntimeError(f"Port {port} is already in use; stop the existing service before running dev.py")
        except OSError:
            pass

    def check_services_running():
        if any(p.poll() is not None for p in processes):
            raise RuntimeError("A service exited during startup; inspect its output above")

    def start(arguments, cwd, extra=None):
        env = {**os.environ, **LOCAL_ENV, **(extra or {})}
        process = subprocess.Popen(arguments, cwd=cwd, env=env, start_new_session=os.name != "nt")
        processes.append(process)
        return process

    def wait_ready(url, timeout=120):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            check_services_running()
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        return
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.25)
        raise RuntimeError(f"Service did not become ready: {url}")

    def stop(*_):
        raise KeyboardInterrupt

    def wait_worker_ready(path, label, timeout=120):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            check_services_running()
            if path.exists():
                return
            time.sleep(0.25)
        raise RuntimeError(f"{label} did not become ready; inspect its output above")

    signal.signal(signal.SIGTERM, stop)
    try:
        ensure_port_available(8004)
        ensure_port_available(5176)
        print("Starting backend...", flush=True)
        start([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8004"], ROOT / "backend")
        wait_ready("http://127.0.0.1:8004/ready")
        print("Backend ready. Starting notification worker...", flush=True)
        start([sys.executable, "-m", "workers.notification_worker"], ROOT / "backend",
              {"AGIS_NOTIFICATION_READY_FILE": str(notification_ready_file)})
        wait_worker_ready(notification_ready_file, "Notification worker")
        print("Notification worker ready. Starting combined agent worker...", flush=True)
        start([sys.executable, "-m", "workers.combined_agent_worker"], ROOT / "backend",
              {"AGIS_WORKER_READY_FILE": str(worker_ready_file)})
        wait_worker_ready(worker_ready_file, "Agent worker")
        print("Combined agent worker ready. Starting frontend...", flush=True)
        start(["npm.cmd" if os.name == "nt" else "npm", "run", "dev"], ROOT / "frontend")
        wait_ready("http://127.0.0.1:5176")
        check_services_running()
        print("AGIS ready: http://localhost:5176 (Ctrl+C stops all services)", flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
        raise RuntimeError("A service stopped unexpectedly")
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        worker_ready_file.unlink(missing_ok=True)
        notification_ready_file.unlink(missing_ok=True)
        for process in reversed(processes):
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                else:
                    os.killpg(process.pid, signal.SIGTERM)
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
