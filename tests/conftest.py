"""tests/conftest.py — Shared pytest configuration for all AGIS-2026 tests.

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

# Tests never authenticate against real services or use developer secrets.
for key, value in {
    "JWT_SECRET": "test-only-signing-secret-at-least-32-characters",
    "WORKER_INTERNAL_SECRET": "test-only-worker-secret-32-characters",
    "MONGODB_URI": "mongodb://127.0.0.1:27018",
    "MONGODB_DB_NAME": "agis_tests",
    "KAFKA_BOOTSTRAP_SERVERS": "127.0.0.1:19092",
    "PES_AUTH_URL": "http://invalid.test/auth",
    "TAVILY_API_KEY": "test-only", "OPENAI_API_KEY": "test-only",
    "OPENAI_MODEL_NAME": "openai/test-model", "LM_STUDIO_URL": "http://invalid.test/v1",
    "FERNET_KEY": "", "ENVIRONMENT": "test", "JWT_EXPIRY_MINUTES": "15",
}.items():
    os.environ[key] = value
