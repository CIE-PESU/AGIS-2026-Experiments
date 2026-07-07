"""
AuditLog repository — append-only writes to `audit_logs` collection.
No update or delete methods. Immutable by design.
"""

from typing import Optional, Any
from datetime import datetime

from app.models.audit import AuditLog, AuditEvent
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self) -> None:
        super().__init__(AuditLog)

    async def create_event(
        self,
        event: AuditEvent | str,
        actor: str,
        actor_role: str,
        metadata: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Write an immutable audit log entry.
        session_id is optional — auth events (login, logout) are not tied to a session.
        """
        log = AuditLog(
            session_id=session_id,
            event=event,  # type: ignore[arg-type]
            actor=actor,
            actor_role=actor_role,
            metadata=metadata or {},
            timestamp=datetime.utcnow(),
        )
        await log.insert()
        return log

    async def find_by_session(
        self,
        session_id: str,
        page: int = 1,
        limit: int = 50,
    ) -> list[AuditLog]:
        """
        Return chronological audit trail for a session.
        Sorted ascending by timestamp (oldest first).
        """
        skip = (page - 1) * limit
        return (
            await AuditLog.find(AuditLog.session_id == session_id)
            .sort(+AuditLog.timestamp)  # type: ignore[arg-type]
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def count_by_session(self, session_id: str) -> int:
        return await AuditLog.find(AuditLog.session_id == session_id).count()

    async def find_all_system(
        self,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Admin query — returns system-wide audit logs with time and event filters."""
        query = AuditLog.find_all()
        
        if filters:
            if filters.get("event"):
                query = AuditLog.find(AuditLog.event == filters["event"])
            if filters.get("actor"):
                query = AuditLog.find(AuditLog.actor == filters["actor"])
            if filters.get("session_id"):
                query = AuditLog.find(AuditLog.session_id == filters["session_id"])
            if filters.get("from_date"):
                query = AuditLog.find(AuditLog.timestamp >= filters["from_date"])
            if filters.get("to_date"):
                query = AuditLog.find(AuditLog.timestamp <= filters["to_date"])
                
        skip = (page - 1) * limit
        return await query.sort(-AuditLog.timestamp).skip(skip).limit(limit).to_list() # type: ignore[arg-type]

    async def count_system_events(self, event_type: str, since: datetime) -> int:
        """Helper for metrics to count specific events (like logins or errors) in a timeframe."""
        return await AuditLog.find(
            AuditLog.event == event_type,
            AuditLog.timestamp >= since
        ).count()

audit_repo = AuditRepository()
