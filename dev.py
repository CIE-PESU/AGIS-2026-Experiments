#!/usr/bin/env python3
"""Run with `python dev.py` using the project virtual environment; stop all services on failure or Ctrl+C."""
from __future__ import annotations
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
LOCAL_ENV = {"WORKER_BACKEND_URL": "http://127.0.0.1:8004", "VITE_BACKEND_URL": "http://127.0.0.1:8004"}


def main() -> int:
    processes: list[subprocess.Popen] = []
    def start(arguments, cwd, extra=None):
        env = {**os.environ, **LOCAL_ENV, **(extra or {})}
        process = subprocess.Popen(arguments, cwd=cwd, env=env, start_new_session=os.name != "nt")
        processes.append(process)
        return process

    def wait_ready(url, timeout=120):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(p.poll() is not None for p in processes):
                raise RuntimeError("A service exited during startup; inspect its output above")
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

    signal.signal(signal.SIGTERM, stop)
    try:
        start([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8004"], ROOT / "backend")
        wait_ready("http://127.0.0.1:8004/ready")
        start([sys.executable, "-m", "workers.combined_agent_worker"], ROOT / "backend")
        start(["npm", "run", "dev"], ROOT / "frontend")
        wait_ready("http://127.0.0.1:5176")
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
        for process in reversed(processes):
            if process.poll() is None:
                if os.name == "nt":
                    process.terminate()
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
