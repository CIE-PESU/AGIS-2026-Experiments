"""Offline setup diagnostic. Run with the same Python used for dev.py."""

from __future__ import annotations

import importlib.metadata
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures = []
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Python: {platform.python_version()} ({sys.executable})")
    if not (3, 12) <= sys.version_info[:2] < (3, 14):
        failures.append("Use Python 3.12 or 3.13 and recreate the root .venv.")
    for filename in (
        "backend/core/__init__.py",
        "backend/core/processes.py",
        "backend/core/llm_provider.py",
        "backend/main.py",
        "backend/workers/agent_runner.py",
        "DFV-agent/main.py",
        "customer-interview-planner-agent/customer_interview_planner.py",
        "quickstart-agent/quickstart_agent/main.py",
        "TIPSC-Agent/src/main.py",
    ):
        if not (ROOT / filename).is_file():
            failures.append(f"Missing {filename}: obtain the complete repository checkout.")
    # Metadata works without importing agents or reading/printing credentials.
    for name in (
        "fastapi",
        "uvicorn",
        "pydantic-settings",
        "python-dotenv",
        "httpx",
        "filelock",
        "motor",
        "beanie",
        "aiokafka",
        "crewai",
        "crewai-tools",
        "litellm",
    ) + (("pywin32",) if sys.platform == "win32" else ()):
        try:
            importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            failures.append(
                f"Missing Python dependency: {name}. Install root requirements in this environment."
            )
    if not (ROOT / ".env").is_file():
        failures.append(
            "Missing root .env: run python scripts/init_env.py, then configure provider keys."
        )
    node = shutil.which("node")
    if node:
        try:
            result = subprocess.run(
                [node, "--version"], capture_output=True, text=True, timeout=10, check=True
            )
            version = tuple(map(int, re.findall(r"\d+", result.stdout)[:3]))
            if version < (22, 13, 0):
                failures.append("Node 22.13+ is required; use Node 24 for the tested setup.")
            print(f"Node: {result.stdout.strip()}")
        except (OSError, subprocess.SubprocessError, ValueError):
            failures.append("Node is installed but could not report its version.")
    else:
        failures.append("Node is missing from PATH; install Node 24.")
    if not (ROOT / "frontend/node_modules/vite/bin/vite.js").is_file():
        failures.append(
            "Frontend dependencies missing: run npm ci --prefix frontend on this machine."
        )
    if not shutil.which("docker"):
        failures.append(
            "Docker is missing from PATH; install/start Docker Desktop with Linux containers."
        )
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1
    print(
        "Offline setup checks passed. This does not check running Docker services or provider credentials."
    )
    print("Next: docker compose -f backend/docker-compose.yml up -d --wait, then python dev.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
