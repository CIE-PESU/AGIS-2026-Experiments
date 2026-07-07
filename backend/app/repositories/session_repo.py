"""
Session repository — the ONLY layer that reads/writes the `sessions` collection.
All queries apply ownership filters at this layer, not in services or routes.
"""

from datetime import datetime
from typing import Optional, Any
from beanie.operators import In, NotIn

from app.models.session import Session
from app.state_machine.states import SessionStatus
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    def __init__(self) -> None:
        super().__init__(Session)

    async def create(self, session_data: dict[str, Any]) -> Session:
        """Create and persist a new session document."""
        session = Session(**session_data)
        await session.insert()
        return session

    async def find_by_id(self, session_id: str) -> Optional[Session]:
        """Fetch session by _id. No ownership filter — used by admin and workers."""
        return await Session.get(session_id)

    async def find_by_id_and_student(
        self, session_id: str, student_id: str
    ) -> Optional[Session]:
        """
        Ownership-filtered fetch for student access.
        Returns None if session exists but belongs to a different student.
        This intentionally returns None (not raises 403) to prevent information leakage.
        """
        return await Session.find_one(
            Session.id == session_id,  # type: ignore[arg-type]
            Session.student_id == student_id,
        )

    async def find_by_student(
        self,
        student_id: str,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Session]:
        """Paginated sessions for a student. Excludes archived by default."""
        query = Session.find(
            Session.student_id == student_id,
            NotIn(Session.status, [SessionStatus.ARCHIVED]),  # type: ignore[arg-type]
        )
        if filters:
            if "status" in filters:
                query = Session.find(
                    Session.student_id == student_id,
                    Session.status == filters["status"],
                )
        skip = (page - 1) * limit
        return await query.skip(skip).limit(limit).sort(-Session.created_at).to_list()  # type: ignore[arg-type]

    async def find_by_teams(
        self,
        team_ids: list[str],
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Session]:
        """
        Mentor query — returns sessions where team_id is in the mentor's supervised teams.
        Returns empty list (not error) if team_ids is empty.
        """
        if not team_ids:
            return []

        query = Session.find(In(Session.team_id, team_ids))  # type: ignore[arg-type]

        if filters:
            if "status" in filters and filters["status"]:
                query = Session.find(
                    In(Session.team_id, team_ids),  # type: ignore[arg-type]
                    Session.status == filters["status"],
                )
            if "team_id" in filters and filters["team_id"]:
                query = Session.find(
                    Session.team_id == filters["team_id"],
                )

        skip = (page - 1) * limit
        return await query.skip(skip).limit(limit).sort(-Session.created_at).to_list()  # type: ignore[arg-type]

    async def update_status(
        self,
        session_id: str,
        new_status: SessionStatus,
        expected_version: int,
    ) -> bool:
        """
        Optimistic concurrency lock.
        Only updates if the current version matches expected_version.
        Returns False if the version has changed (another update won)  — caller retries or raises conflict.
        """
        result = await Session.find_one(
            Session.id == session_id,  # type: ignore[arg-type]
            Session.version == expected_version,
        ).update(
            {
                "$set": {
                    "status": new_status,
                    "updated_at": datetime.utcnow(),
                },
                "$inc": {"version": 1},
            }
        )
        return result is not None and result.modified_count == 1

    async def update_flow_output(
        self,
        session_id: str,
        flow: str,
        output: dict[str, Any],
        new_status: SessionStatus,
        expected_version: Optional[int] = None,
    ) -> bool:
        """
        Write the AI output for a flow and advance session status atomically.
        `flow` is one of: "tipsc", "dfv", "discovery".
        Uses version field for optimistic concurrency if expected_version is provided.
        """
        if expected_version is not None:
            query = Session.find_one(
                Session.id == session_id,  # type: ignore[arg-type]
                Session.version == expected_version,
            )
        else:
            query = Session.find_one(Session.id == session_id)  # type: ignore[arg-type]

        result = await query.update(
            {
                "$set": {
                    flow: output,
                    "status": new_status,
                    "updated_at": datetime.utcnow(),
                },
                "$inc": {"version": 1},
            }
        )
        return result is not None and result.modified_count == 1

    async def update_flow_failure(
        self,
        session_id: str,
        new_status: SessionStatus,
        failure_metadata: dict[str, Any],
    ) -> bool:
        """
        Write the flow failure metadata and advance session status atomically.
        """
        result = await Session.find_one(Session.id == session_id).update(  # type: ignore[arg-type]
            {
                "$set": {
                    "failure_metadata": failure_metadata,
                    "status": new_status,
                    "updated_at": datetime.utcnow(),
                },
                "$inc": {"version": 1},
            }
        )
        return result is not None and result.modified_count == 1

    async def archive(self, session_id: str) -> bool:
        """Soft-archive a session. Sets status=ARCHIVED and archived_at=now()."""
        session = await Session.get(session_id)
        if session is None:
            return False
        session.status = SessionStatus.ARCHIVED
        session.archived_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        session.version += 1
        await session.save()
        return True

    async def find_active_by_student(self, student_id: str) -> Optional[Session]:
        """
        Returns the student's active (non-archived) session, or None.
        Used to enforce the one-active-session-per-student rule.
        """
        return await Session.find_one(
            Session.student_id == student_id,
            NotIn(Session.status, [SessionStatus.ARCHIVED]),  # type: ignore[arg-type]
        )

    async def find_by_idempotency_key(self, key: str) -> Optional[Session]:
        """Deduplication — returns existing session if idempotency key was already used."""
        return await Session.find_one(Session.idempotency_key == key)

    async def update_dfv_inputs(self, session_id: str, dfv_inputs: dict) -> bool:
        """
        Persist the student-supplied DFV context inputs on the session document.
        Called by FlowService.trigger_dfv() before publishing the Kafka event.
        `dfv_inputs` is expected to have keys:
          desirability_context, feasibility_context, viability_context
        """
        result = await Session.find_one(Session.id == session_id).update(  # type: ignore[arg-type]
            {
                "$set": {
                    "dfv_inputs": dfv_inputs,
                    "updated_at": datetime.utcnow(),
                }
            }
        )
        return result is not None and result.modified_count == 1

    async def set_correlation_id(self, session_id: str, correlation_id: str) -> None:
        """Store the Kafka correlation_id on the session so workers can validate it."""
        await Session.find_one(Session.id == session_id).update(  # type: ignore[arg-type]
            {"$set": {"correlation_id": correlation_id, "updated_at": datetime.utcnow()}}
        )

    async def count_by_teams(
        self,
        team_ids: list[str],
        filters: Optional[dict[str, Any]] = None,
    ) -> int:
        """
        Count non-archived sessions across a set of teams.
        Used by mentor_service for pagination totals.
        Returns 0 if team_ids is empty.
        """
        if not team_ids:
            return 0

        query = Session.find(
            In(Session.team_id, team_ids),  # type: ignore[arg-type]
            NotIn(Session.status, [SessionStatus.ARCHIVED]),  # type: ignore[arg-type]
        )

        if filters:
            if filters.get("status"):
                query = Session.find(
                    In(Session.team_id, team_ids),  # type: ignore[arg-type]
                    Session.status == filters["status"],
                )
            if filters.get("team_id"):
                query = Session.find(
                    Session.team_id == filters["team_id"],
                    NotIn(Session.status, [SessionStatus.ARCHIVED]),  # type: ignore[arg-type]
                )

        return await query.count()

    async def find_all_admin(
        self,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Session]:
        """Admin query — returns all sessions across the platform with optional filtering."""
        query = Session.find_all()
        
        if filters:
            if filters.get("status"):
                query = Session.find(Session.status == filters["status"])
            if filters.get("team_id"):
                query = Session.find(Session.team_id == filters["team_id"])
            if filters.get("student_id"):
                query = Session.find(Session.student_id == filters["student_id"])
                
        skip = (page - 1) * limit
        return await query.skip(skip).limit(limit).sort(-Session.created_at).to_list() # type: ignore[arg-type]

    async def get_system_metrics(self) -> dict[str, Any]:
        """Runs MongoDB aggregations to compute platform metrics."""
        # Active sessions (not archived)
        active_sessions = await Session.find(
            NotIn(Session.status, [SessionStatus.ARCHIVED]) # type: ignore[arg-type]
        ).count()
        
        # Sessions grouped by status
        status_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        status_results = await Session.aggregate(status_pipeline).to_list()
        sessions_by_status = {item["_id"]: item["count"] for item in status_results if item["_id"]}
        
        # Average TIPSC duration
        duration_pipeline = [
            {"$match": {"tipsc.duration_seconds": {"$exists": True}}},
            {"$group": {"_id": None, "avg_duration": {"$avg": "$tipsc.duration_seconds"}}}
        ]
        duration_results = await Session.aggregate(duration_pipeline).to_list()
        avg_tipsc = int(duration_results[0]["avg_duration"]) if duration_results else 0
        
        return {
            "active_sessions": active_sessions,
            "sessions_by_status": sessions_by_status,
            "average_tipsc_duration_seconds": avg_tipsc
        }

session_repo = SessionRepository()

