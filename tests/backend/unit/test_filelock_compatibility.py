"""Validate the third-party locking calls affected by our security override."""
from contextlib import ExitStack

import pytest
from cachecontrol.caches import FileCache
from filelock import FileLock, SoftFileLock, Timeout
from huggingface_hub.utils import WeakFileLock


def test_litellm_profile_lock_patterns(tmp_path):
    path = tmp_path / "settings.lock"
    with ExitStack() as stack:
        lock = stack.enter_context(FileLock(str(path), timeout=10, mode=0o600))
        assert lock.is_locked
        with pytest.raises(Timeout):
            FileLock(str(path), timeout=0).acquire()
    with FileLock(str(path), timeout=0, mode=0o600):
        pass


def test_huggingface_and_cachecontrol_file_locks(tmp_path):
    with WeakFileLock(tmp_path / "hub.lock", timeout=1) as lock:
        assert lock.is_locked
    cache = FileCache(str(tmp_path / "cache"))
    cache.set("test-key", b"cached bytes")
    assert cache.get("test-key") == b"cached bytes"
    cache.delete("test-key")
    assert cache.get("test-key") is None
    # Hugging Face falls back to this when flock is unavailable.
    with SoftFileLock(tmp_path / "fallback.lock", timeout=1) as lock:
        assert lock.is_locked
