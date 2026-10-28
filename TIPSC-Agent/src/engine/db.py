"""Run-scoped, optimistic MongoDB persistence for TIPSC tasks."""
from contextvars import ContextVar
from datetime import datetime, timezone
from bson import ObjectId

# Context is local to each pipeline task, never shared between sessions/tasks.
_snapshot: ContextVar[tuple[str, str | None, int] | None] = ContextVar("tipsc_snapshot", default=None)
_ACTIVE = ["queued", "pre_eval", "validation_running", "regulatory_running", "ethics_running",
           "tipsc_running", "tipsc_reevaluation", "waiting_for_founder"]


def _to_oid(session_id: str):
    try:
        return ObjectId(session_id)
    except Exception:
        return session_id


class SessionStore:
    def __init__(self, collection):
        self._collection = collection

    async def update_session(self, session_id: str, patch: dict):
        snapshot = _snapshot.get()
        if snapshot is None or snapshot[0] != session_id:
            raise RuntimeError("Read session before updating pipeline state")
        _, correlation_id, version = snapshot
        predicate = {"_id": _to_oid(session_id), "correlation_id": correlation_id,
                     "version": version, "status": {"$in": _ACTIVE}}
        patch = {**patch, "updated_at": datetime.now(timezone.utc)}
        result = await self._collection.update_one(predicate, {"$set": patch, "$inc": {"version": 1}})
        if result.matched_count != 1:
            raise RuntimeError("Pipeline run was superseded, cancelled, or modified")
        _snapshot.set((session_id, correlation_id, version + 1))

    async def get_session(self, session_id: str) -> dict | None:
        session = await self._collection.find_one({"_id": _to_oid(session_id)})
        snapshot = _snapshot.get()
        if session is not None:
            if snapshot and snapshot[0] == session_id and snapshot[1] != session.get("correlation_id"):
                raise RuntimeError("Pipeline run was superseded")
            _snapshot.set((session_id, session.get("correlation_id"), session.get("version", 0)))
        return session

    async def get_active_session_by_user(self, student_id: str) -> dict | None:
        return await self._collection.find_one(
            {"student_id": student_id, "status": "waiting_for_founder"}, sort=[("updated_at", -1)])
