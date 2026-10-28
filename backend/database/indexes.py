"""
Index definitions — created on startup (idempotent).
All indexes mirror backend-arch.md Section 8.3.
"""

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from core.config import settings
from database.mongodb import get_client

logger = logging.getLogger(__name__)


async def create_indexes() -> None:
    """Create all required indexes. Safe to call multiple times (idempotent)."""
    client: AsyncIOMotorClient = get_client()
    db = client[settings.MONGODB_DB_NAME]

    # ── sessions ──────────────────────────────────────────────────────────────
    sessions = db["sessions"]

    await sessions.create_index("student_id", name="ix_sessions_student_id")
    await sessions.create_index("team_id", name="ix_sessions_team_id")
    await sessions.create_index("status", name="ix_sessions_status")
    await sessions.create_index(
        [("student_id", 1), ("status", 1)],
        name="ix_sessions_student_status",
    )
    await sessions.create_index(
        [("created_at", -1)],
        name="ix_sessions_created_at_desc",
    )

    # ── audit_logs ────────────────────────────────────────────────────────────
    audit_logs = db["audit_logs"]

    await audit_logs.create_index("session_id", name="ix_audit_session_id")
    await audit_logs.create_index("timestamp", name="ix_audit_timestamp")
    await audit_logs.create_index(
        [("session_id", 1), ("timestamp", 1)],
        name="ix_audit_session_timestamp",
    )

    # ── mentor_comments ───────────────────────────────────────────────────────
    mentor_comments = db["mentor_comments"]

    await mentor_comments.create_index("session_id", name="ix_comments_session_id")

    # ── refresh_tokens ────────────────────────────────────────────────────────
    refresh_tokens = db["refresh_tokens"]

    existing = await refresh_tokens.index_information()
    desired: list[tuple[str, dict[str, Any], str]] = [
        ("token_hash", {"unique": True}, "ix_refresh_tokens_hash"),
        ("expires_at", {"expireAfterSeconds": 0}, "ix_refresh_tokens_ttl"),
    ]
    for field, options, default_name in desired:
        matching = [
            (name, data) for name, data in existing.items() if data.get("key") == [(field, 1)]
        ]
        name = default_name
        for old_name, data in matching:
            if all(data.get(key) == value for key, value in options.items()):
                name = old_name
                break
            # Replace only the obsolete single-field index, never application records.
            await refresh_tokens.drop_index(old_name)
        await refresh_tokens.create_index(field, name=name, **options)

    # ── idempotency_keys ──────────────────────────────────────────────────────
    idempotency_keys = db["idempotency_keys"]

    await idempotency_keys.create_index(
        "key",
        unique=True,
        name="ix_idempotency_key",
    )
    await idempotency_keys.create_index(
        "expires_at",
        expireAfterSeconds=0,
        name="ix_idempotency_ttl",
    )

    logger.info("All MongoDB indexes created successfully.")
