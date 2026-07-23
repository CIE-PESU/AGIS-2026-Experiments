"""
repositories/session_repo.py

Single repository layer for the sessions collection.

All MongoDB reads/writes for sessions must go through this repository.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from beanie import PydanticObjectId
from beanie.operators import In, NotIn

from models.session import Session, StateTransition
from repositories.base import BaseRepository
from state_machine.states import SessionStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SessionRepository(BaseRepository[Session]):

    def __init__(self) -> None:
        super().__init__(Session)


    # ──────────────────────────────────────────────────────────────────────
    # CREATE
    # ──────────────────────────────────────────────────────────────────────

    async def create(
        self,
        session_data: dict[str, Any],
    ) -> Session:

        session = Session(**session_data)

        await session.insert()

        return session


    # ──────────────────────────────────────────────────────────────────────
    # BASIC LOOKUPS
    # ──────────────────────────────────────────────────────────────────────

    async def find_by_id(
        self,
        session_id: str,
    ) -> Optional[Session]:

        return await Session.get(session_id)


    async def find_by_id_and_student(
        self,
        session_id: str,
        student_id: str,
    ) -> Optional[Session]:

        session = await Session.get(session_id)

        if (
            session
            and session.student_id == student_id
        ):
            return session

        return None


    async def find_by_student(
        self,
        student_id: str,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Session]:

        expressions = [
            Session.student_id == student_id,
            NotIn(
                Session.status,
                [SessionStatus.ARCHIVED],
            ),
        ]

        if filters and filters.get("status"):

            expressions.append(
                Session.status == filters["status"]
            )

        skip = (page - 1) * limit

        return (
            await Session.find(*expressions)
            .skip(skip)
            .limit(limit)
            .sort(-Session.created_at)
            .to_list()
        )


    async def find_active_by_student(
        self,
        student_id: str,
    ) -> Optional[Session]:

        return await Session.find_one(
            Session.student_id == student_id,
            Session.team_id != "",
            NotIn(
                Session.status,
                [SessionStatus.ARCHIVED],
            ),
        )


    async def find_by_idempotency_key(
        self,
        key: str,
    ) -> Optional[Session]:

        return await Session.find_one(
            Session.idempotency_key == key
        )


    # ──────────────────────────────────────────────────────────────────────
    # TIPSC FOLLOW-UP LOOKUPS
    # ──────────────────────────────────────────────────────────────────────

    async def get_active_session_by_user(
        self,
        student_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Return the newest session waiting for founder input.

        Used by TIPSC follow-up APIs.
        """

        session = (
            await Session.find_one(
                Session.student_id == student_id,
                Session.status
                == SessionStatus.WAITING_FOR_FOUNDER,
            )
            .sort(-Session.updated_at)
        )

        if session is None:
            return None

        data = session.model_dump()

        data["_id"] = str(session.id)

        return data


    async def find_waiting_followup(
        self,
        session_id: str,
        student_id: str,
    ) -> Optional[Session]:
        """
        Fetch a founder-owned session only when it is waiting for an answer.
        """

        return await Session.find_one(
            Session.id == PydanticObjectId(session_id),
            Session.student_id == student_id,
            Session.status
            == SessionStatus.WAITING_FOR_FOUNDER,
        )


    # ──────────────────────────────────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────────────────────────────────

    async def update_status(
        self,
        session_id: str,
        new_status: SessionStatus,
        expected_version: int,
        current_status: str = "",
        actor: str = "system",
        trigger: str = "update_status",
    ) -> bool:

        now = utc_now()

        transition = StateTransition(
            from_status=current_status,
            to_status=new_status.value,
            actor=actor,
            trigger=trigger,
        )

        result = await Session.find_one(
            Session.id == PydanticObjectId(session_id),
            Session.version == expected_version,
        ).update(
            {
                "$set": {
                    "status": new_status.value,
                    "updated_at": now,
                },
                "$inc": {
                    "version": 1,
                },
                "$push": {
                    "state_history": (
                        transition.model_dump()
                    ),
                },
            }
        )

        return (
            result is not None
            and result.modified_count == 1
        )


    # ──────────────────────────────────────────────────────────────────────
    # GENERIC PIPELINE PATCH
    # ──────────────────────────────────────────────────────────────────────

    async def update_pipeline_state(
        self,
        session_id: str,
        patch: dict[str, Any],
    ) -> bool:
        """
        Apply a generic TIPSC pipeline patch.

        Intended for direct in-process TIPSC execution.

        Examples:
            preeval
            validation
            regulatory
            ethics
            compliance_context
            tipsc
            pending_question
            followup_turn
            status
            error
        """

        patch = dict(patch)

        patch["updated_at"] = utc_now()

        result = await Session.find_one(
            Session.id == PydanticObjectId(session_id)
        ).update(
            {
                "$set": patch,
                "$inc": {
                    "version": 1,
                },
            }
        )

        return (
            result is not None
            and result.modified_count == 1
        )


    # ──────────────────────────────────────────────────────────────────────
    # FLOW OUTPUTS
    # ──────────────────────────────────────────────────────────────────────

    async def update_flow_output(
        self,
        session_id: str,
        flow: str,
        output: dict[str, Any],
        new_status: SessionStatus,
        expected_version: Optional[int] = None,
    ) -> bool:

        if expected_version is not None:

            query = Session.find_one(
                Session.id
                == PydanticObjectId(session_id),
                Session.version == expected_version,
            )

        else:

            query = Session.find_one(
                Session.id
                == PydanticObjectId(session_id)
            )

        result = await query.update(
            {
                "$set": {
                    flow: output,
                    "status": new_status.value,
                    "updated_at": utc_now(),
                },
                "$inc": {
                    "version": 1,
                },
            }
        )

        return (
            result is not None
            and result.modified_count == 1
        )


    async def update_flow_failure(
        self,
        session_id: str,
        new_status: SessionStatus,
        failure_metadata: dict[str, Any],
    ) -> bool:

        result = await Session.find_one(
            Session.id
            == PydanticObjectId(session_id)
        ).update(
            {
                "$set": {
                    "failure_metadata": failure_metadata,
                    "status": new_status.value,
                    "updated_at": utc_now(),
                },
                "$inc": {
                    "version": 1,
                },
            }
        )

        return (
            result is not None
            and result.modified_count == 1
        )


    # ──────────────────────────────────────────────────────────────────────
    # FOLLOW-UP ANSWERS
    # ──────────────────────────────────────────────────────────────────────

    async def submit_followup_answer(
        self,
        session_id: str,
        answer: str,
        expected_version: int,
    ) -> bool:
        """
        Atomically accept a founder answer.

        This repository method only persists the answer and moves the session
        into TIPSC_REEVALUATION.

        AsyncPipelineExecutor.resume_after_followup() owns the actual
        re-evaluation logic.
        """

        result = await Session.find_one(
            Session.id
            == PydanticObjectId(session_id),
            Session.version == expected_version,
            Session.status
            == SessionStatus.WAITING_FOR_FOUNDER,
        ).update(
            {
                "$set": {
                    "pending_answer": answer,
                    "status": (
                        SessionStatus
                        .TIPSC_REEVALUATION
                        .value
                    ),
                    "updated_at": utc_now(),
                },
                "$inc": {
                    "version": 1,
                },
            }
        )

        return (
            result is not None
            and result.modified_count == 1
        )


    async def append_followup_exchange(
        self,
        session_id: str,
        question: str,
        answer: str,
        turn: int,
    ) -> bool:
        """
        Append one completed founder Q&A exchange.

        The pending question is cleared after the exchange is stored.
        """

        exchange = {
            "question": question,
            "answer": answer,
            "turn": turn,
            "answered_at": utc_now(),
        }

        result = await Session.find_one(
            Session.id
            == PydanticObjectId(session_id)
        ).update(
            {
                "$push": {
                    "followup_history": exchange,
                },
                "$set": {
                    "pending_question": None,
                    "pending_answer": None,
                    "updated_at": utc_now(),
                },
                "$inc": {
                    "version": 1,
                },
            }
        )

        return (
            result is not None
            and result.modified_count == 1
        )


    # ──────────────────────────────────────────────────────────────────────
    # DFV
    # ──────────────────────────────────────────────────────────────────────

    async def update_dfv_inputs(
        self,
        session_id: str,
        dfv_inputs: dict[str, Any],
    ) -> bool:

        result = await Session.find_one(
            Session.id
            == PydanticObjectId(session_id)
        ).update(
            {
                "$set": {
                    "dfv_inputs": dfv_inputs,
                    "updated_at": utc_now(),
                },
                "$unset": {
                    "dfv": ""
                }
            }
        )

        return (
            result is not None
            and result.modified_count == 1
        )
    # ──────────────────────────────────────────────────────────────────────
# DISCOVERY
# ──────────────────────────────────────────────────────────────────────

    async def update_discovery_inputs(
        self,
        session_id: str,
        discovery_inputs: dict[str, Any],
    ) -> bool:

        result = await Session.find_one(
            Session.id == PydanticObjectId(session_id)
        ).update(
            {
                "$set": {
                    "discovery_inputs": discovery_inputs,
                    "updated_at": utc_now(),
                },
                "$unset": {
                    "discovery": ""
                }
            }
        )

        return (
            result is not None
            and result.modified_count == 1
        )


    # ──────────────────────────────────────────────────────────────────────
    # ATOMIC CAS FLOW STARTS
    # ──────────────────────────────────────────────────────────────────────

    async def atomic_start_dfv_flow(
        self,
        session_id: str,
        correlation_id: str,
        dfv_inputs: dict[str, Any],
    ) -> bool:
        """
        Atomically transition session from allowed pre-DFV status (TIPSC_COMPLETED, DFV_FAILED)
        to DFV_WAITING, setting correlation_id, flow_started_at, and dfv_inputs in one atomic operation.

        Returns True if CAS won (update modified/matched 1 document), False if CAS lost (already waiting/running or invalid state).
        """
        now = utc_now()
        allowed_statuses = [
            SessionStatus.TIPSC_COMPLETED.value,
            SessionStatus.DFV_FAILED.value,
        ]
        result = await Session.find_one(
            Session.id == PydanticObjectId(session_id),
            In("status", allowed_statuses),
        ).update(
            {
                "$set": {
                    "correlation_id": correlation_id,
                    "dfv_inputs": dfv_inputs,
                    "status": SessionStatus.DFV_WAITING.value,
                    "flow_started_at": now,
                    "updated_at": now,
                },
                "$inc": {"version": 1},
            }
        )
        if result is None:
            return False
        matched = getattr(result, "matched_count", 0)
        modified = getattr(result, "modified_count", 0)
        return matched == 1 or modified == 1

    async def atomic_start_discovery_flow(
        self,
        session_id: str,
        correlation_id: str,
        discovery_inputs: dict[str, Any],
    ) -> bool:
        """
        Atomically transition session from allowed pre-Discovery status (DFV_COMPLETED, DISCOVERY_FAILED)
        to DISCOVERY_WAITING, setting correlation_id, flow_started_at, and discovery_inputs in one atomic operation.

        Returns True if CAS won (update modified/matched 1 document), False if CAS lost (already waiting/running or invalid state).
        """
        now = utc_now()
        allowed_statuses = [
            SessionStatus.DFV_COMPLETED.value,
            SessionStatus.DISCOVERY_FAILED.value,
        ]
        result = await Session.find_one(
            Session.id == PydanticObjectId(session_id),
            In("status", allowed_statuses),
        ).update(
            {
                "$set": {
                    "correlation_id": correlation_id,
                    "discovery_inputs": discovery_inputs,
                    "status": SessionStatus.DISCOVERY_WAITING.value,
                    "flow_started_at": now,
                    "updated_at": now,
                },
                "$inc": {"version": 1},
            }
        )
        if result is None:
            return False
        matched = getattr(result, "matched_count", 0)
        modified = getattr(result, "modified_count", 0)
        return matched == 1 or modified == 1

    async def set_correlation_id(
        self,
        session_id: str,
        correlation_id: str,
    ) -> None:

        await Session.find_one(
            Session.id
            == PydanticObjectId(session_id)
        ).update(
            {
                "$set": {
                    "correlation_id": correlation_id,
                    "updated_at": utc_now(),
                }
            }
        )


    # ──────────────────────────────────────────────────────────────────────
    # ARCHIVE
    # ──────────────────────────────────────────────────────────────────────

    async def archive(
        self,
        session_id: str,
    ) -> bool:

        session = await Session.get(session_id)

        if session is None:
            return False

        session.status = SessionStatus.ARCHIVED

        session.archived_at = utc_now()

        session.updated_at = utc_now()

        session.version += 1

        await session.save()

        return True


    # ──────────────────────────────────────────────────────────────────────
    # MENTOR
    # ──────────────────────────────────────────────────────────────────────

    async def find_by_teams(
        self,
        team_ids: list[str],
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Session]:

        if not team_ids:
            return []

        expressions = [
            In(Session.team_id, team_ids),
        ]

        if filters:

            if filters.get("status"):

                expressions.append(
                    Session.status
                    == filters["status"]
                )

            if filters.get("team_id"):

                expressions.append(
                    Session.team_id
                    == filters["team_id"]
                )

        skip = (page - 1) * limit

        return (
            await Session.find(*expressions)
            .skip(skip)
            .limit(limit)
            .sort(-Session.created_at)
            .to_list()
        )


    async def count_by_teams(
        self,
        team_ids: list[str],
        filters: Optional[dict[str, Any]] = None,
    ) -> int:

        if not team_ids:
            return 0

        expressions = [
            In(Session.team_id, team_ids),
            NotIn(
                Session.status,
                [SessionStatus.ARCHIVED],
            ),
        ]

        if filters:

            if filters.get("status"):

                expressions.append(
                    Session.status
                    == filters["status"]
                )

            if filters.get("team_id"):

                expressions.append(
                    Session.team_id
                    == filters["team_id"]
                )

        return await Session.find(
            *expressions
        ).count()


    # ──────────────────────────────────────────────────────────────────────
    # ADMIN
    # ──────────────────────────────────────────────────────────────────────

    async def find_all_admin(
        self,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Session]:

        expressions = []

        if filters:

            if filters.get("status"):

                expressions.append(
                    Session.status
                    == filters["status"]
                )

            if filters.get("team_id"):

                expressions.append(
                    Session.team_id
                    == filters["team_id"]
                )

            if filters.get("student_id"):

                expressions.append(
                    Session.student_id
                    == filters["student_id"]
                )

        query = (
            Session.find(*expressions)
            if expressions
            else Session.find_all()
        )

        skip = (page - 1) * limit

        return (
            await query
            .skip(skip)
            .limit(limit)
            .sort(-Session.created_at)
            .to_list()
        )


    async def get_system_metrics(
        self,
    ) -> dict[str, Any]:

        active_sessions = await Session.find(
            NotIn(
                Session.status,
                [SessionStatus.ARCHIVED],
            )
        ).count()

        status_pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {
                        "$sum": 1,
                    },
                }
            }
        ]

        status_results = await Session.aggregate(
            status_pipeline
        ).to_list()

        sessions_by_status = {
            item["_id"]: item["count"]
            for item in status_results
            if item["_id"]
        }

        duration_pipeline = [
            {
                "$match": {
                    "tipsc.duration_seconds": {
                        "$exists": True,
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_duration": {
                        "$avg": (
                            "$tipsc.duration_seconds"
                        ),
                    },
                }
            },
        ]

        duration_results = await Session.aggregate(
            duration_pipeline
        ).to_list()

        average_tipsc = (
            int(duration_results[0]["avg_duration"])
            if duration_results
            else 0
        )

        return {
            "active_sessions": active_sessions,
            "sessions_by_status": sessions_by_status,
            "average_tipsc_duration_seconds": (
                average_tipsc
            ),
        }


session_repo = SessionRepository()