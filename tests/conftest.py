"""
tests/conftest.py — Shared pytest configuration for all AGIS-2026 tests.

Adds backend/ to sys.path so all test files can import backend modules
without needing to set PYTHONPATH manually.

Run all unit tests from the repo root:
    pytest tests/backend/unit/ -v
"""
import sys
import os

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)
