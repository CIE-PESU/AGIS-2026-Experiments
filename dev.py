#!/usr/bin/env python3
"""One-command dev server: starts backend, workers, and frontend."""
import subprocess
import signal
import sys
import os

procs = []

def start(cmd, cwd=None, env=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    p = subprocess.Popen(cmd, shell=True, cwd=cwd, env=full_env)
    procs.append(p)
    return p

def cleanup(*_):
    for p in procs:
        p.terminate()
    for p in procs:
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

root = os.path.dirname(os.path.abspath(__file__))
backend = os.path.join(root, "backend")
frontend = os.path.join(root, "frontend")

# Activate venv for backend commands
venv_python = os.path.join(root, ".venv", "bin", "python")
venv_bin = os.path.join(root, ".venv", "bin")

# Backend API
start(f"{venv_python} -m uvicorn main:app --reload --host 0.0.0.0 --port 8000", cwd=backend)

# Give backend time to initialize Kafka, MongoDB, etc.
import time
time.sleep(5)

# Combined Agent Worker (DFV + Discovery)
start(f"{venv_python} -m workers.combined_agent_worker", cwd=backend)

# Notification Worker
start(f"{venv_python} -m workers.notification_worker", cwd=backend)

# Give workers time to connect to Kafka
time.sleep(3)

# Give frontend time to wait for backend readiness
time.sleep(20)

# Frontend
start("npm run dev", cwd=frontend)

print("All services started. Press Ctrl+C to stop.")
for p in procs:
    p.wait()