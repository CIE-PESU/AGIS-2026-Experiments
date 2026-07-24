"""
utils/idempotency.py — Idempotency key helpers for safe POST retries.

HOW IT WORKS:
  1. Client sends `Idempotency-Key: <uuid>` header on POST /sessions.
  2. Service calls `check_and_set(key)` before creating any resource.
  3. If the key is new → proceeds; marks it as seen in MongoDB with 24h TTL.
  4. If the key already exists → returns False; caller returns the original response.

STORAGE:
  - Collection: `idempotency_keys`
  - TTL index on `expires_at` (created by database/indexes.py on startup).

ATOMICITY:
  - Uses MongoDB's `update_one` with `upsert=True` and `setOnInsert` so the
    check-and-set is a single atomic round-trip — no race condition between
    two concurrent requests with the same key.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from database.mongodb import get_client
from core.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Key Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_key(student_id: str, action: str) -> str:
    """
    Build a deterministic idempotency key from a student ID and an action name.

    The key is a SHA-256 hex digest so it is:
      - Fixed-length (64 chars)
      - Safe to store in MongoDB
      - Deterministic: same inputs → same key (useful for auto-retry logic)

    Args:
        student_id : The authenticated user's MongoDB _id string.
        action     : A stable action name, e.g. "create_session".

    Returns:
        A 64-character hex string key.

    Example:
        >>> generate_key("usr_abc123", "create_session")
        "a3f9d2..."
    """
    raw = f"{student_id}:{action}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Atomic Check-and-Set
# ─────────────────────────────────────────────────────────────────────────────

async def check_and_set(key: str, ttl_seconds: int = 86_400) -> bool:
    """
    Atomically check if an idempotency key has been seen before.

    If the key is NEW:
      - Inserts it into the `idempotency_keys` collection with a TTL.
      - Returns True  → caller should proceed with the operation.

    If the key ALREADY EXISTS:
      - Does NOT modify the existing document.
      - Returns False → caller should return the original response without
        performing the operation again.

    Atomicity guarantee:
      MongoDB `update_one` with `upsert=True` and `$setOnInsert` is atomic.
      Two concurrent requests with the same key will race; exactly one will
      perform the upsert and get True; the other will get False.

    Args:
        key         : The idempotency key string (from generate_key or client header).
        ttl_seconds : How long to keep the key before auto-expiry. Default: 24 hours.

    Returns:
        True  — key is fresh; proceed with the write operation.
        False — key already seen; skip the operation (return cached/original response).
    """
    client: AsyncIOMotorClient = get_client()
    db = client[settings.MONGODB_DB_NAME]
    collection = db["idempotency_keys"]

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)

    result = await collection.update_one(
        {"key": key},
        {
            "$setOnInsert": {
                "key": key,
                "created_at": now,
                "expires_at": expires_at,
            }
        },
        upsert=True,
    )

    # upserted_id is set only when a new document was inserted
    is_new = result.upserted_id is not None
    if not is_new:
        logger.debug("Idempotency key already seen: %s", key)
    return is_new
