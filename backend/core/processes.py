"""Own child processes as a tree; never terminate unrelated applications."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock, Timeout

ROOT = Path(__file__).resolve().parents[2]


def child_options() -> dict:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


class ProcessTree:
    """Windows jobs kill descendants even when the immediate parent exits."""

    def __init__(self, pid: int):
        self.pid = pid
        self.job = None
        if sys.platform == "win32":
            import win32api
            import win32con
            import win32job

            job = win32job.CreateJobObject(None, None)
            try:
                limits = win32job.QueryInformationJobObject(
                    job, win32job.JobObjectExtendedLimitInformation
                )
                limits["BasicLimitInformation"]["LimitFlags"] |= (
                    win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                )
                win32job.SetInformationJobObject(
                    job, win32job.JobObjectExtendedLimitInformation, limits
                )
                process = win32api.OpenProcess(
                    win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE, False, pid
                )
                try:
                    win32job.AssignProcessToJobObject(job, process)
                finally:
                    process.Close()
                self.job = job
            except BaseException:
                job.Close()
                # This PID was just started by our caller. Fail closed if ownership cannot be established.
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False
                )
                raise

    def terminate(self, force: bool = False) -> None:
        if sys.platform == "win32":
            if self.job is not None:
                self.job.Close()
                self.job = None
        else:
            try:
                os.killpg(self.pid, signal.SIGKILL if force else signal.SIGTERM)
            except ProcessLookupError:
                pass


@contextmanager
def instance_lock(name: str):
    directory = Path(os.getenv("AGIS_RUNTIME_DIR", str(ROOT / ".local")))
    directory.mkdir(parents=True, exist_ok=True)
    lock = FileLock(directory / f"{name}.lock")
    try:
        lock.acquire(timeout=0)
    except Timeout as exc:
        raise RuntimeError(
            f"Another AGIS {name} instance is already running for this checkout."
        ) from exc
    try:
        yield
    finally:
        lock.release()
