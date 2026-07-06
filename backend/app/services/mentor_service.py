"""
services/mentor_service.py — Business logic for all Mentor API endpoints.

Responsibilities:
  - get_supervised_sessions  : Paginated session list filtered by mentor's teams.
  - get_supervised_session_detail : Full session, validates mentor owns the team.
  - get_mentor_teams         : Full team list with member details + active session counts.

Architecture rules:
  - No HTTP concepts here (no Request, no Response, no status codes).
  - Uses session_repo.find_by_teams() for all session queries.
  - Team ownership check is enforced in this service — NOT in the route handler.
  - Raising SessionNotFoundError for unauthorized team access (not 403) so mentors
    cannot infer the existence of sessions on teams they don't supervise.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from beanie import PydanticObjectId

from app.exceptions.base import SessionNotFoundError
from app.models.session import Session
from app.models.team import Team
from app.models.user import User
from app.repositories.session_repo import session_repo
from app.schemas.mentor import MentorSessionListItem, MentorTeamResponse, TeamMemberInfo
from app.state_machine.states import SessionStatus

logger = logging.getLogger(__name__)


class MentorService:
    """All mentor-scoped business operations."""

    # ── Session list ─────────────────────────────────────────────────────────

    async def get_supervised_sessions(
        self,
        mentor_id: str,
        mentor_team_ids: list[str],
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[MentorSessionListItem], int]:
        """
        Return a paginated summary list of sessions across the mentor's teams.

        - Mentor with no assigned teams → returns ([], 0).
        - Filters supported: "status" (string), "team_id" (string).
        - team_id filter is validated against mentor_team_ids — silently returns
          empty list if mentor does not supervise the requested team.
        - Returns summary shape (MentorSessionListItem) — no full AI outputs.

        Returns:
            Tuple of (items, total_count).
        """
        if not mentor_team_ids:
            return [], 0

        # If a team_id filter is given, validate the mentor actually supervises it.
        # If not, return empty list — don't reveal that the team exists.
        if filters and filters.get("team_id"):
            if filters["team_id"] not in mentor_team_ids:
                return [], 0

        sessions = await session_repo.find_by_teams(
            team_ids=mentor_team_ids,
            filters=filters,
            page=page,
            limit=limit,
        )

        # Count total for pagination — uses same filters, no limit/skip
        total_sessions = await session_repo.count_by_teams(
            team_ids=mentor_team_ids,
            filters=filters,
        )

        # Resolve team names and student names in bulk to avoid N+1 queries
        team_ids_needed = {s.team_id for s in sessions}
        student_ids_needed = {s.student_id for s in sessions}

        teams_map: dict[str, Team] = {}
        for tid in team_ids_needed:
            try:
                team = await Team.get(PydanticObjectId(tid))
                if team:
                    teams_map[tid] = team
            except Exception:
                pass

        students_map: dict[str, User] = {}
        for uid in student_ids_needed:
            try:
                user = await User.get(PydanticObjectId(uid))
                if user:
                    students_map[uid] = user
            except Exception:
                pass

        items: list[MentorSessionListItem] = []
        for session in sessions:
            team = teams_map.get(session.team_id)
            student = students_map.get(session.student_id)

            # Extract TIPSC summary if available
            tipsc_score: Optional[int] = None
            ready_for_dfv: Optional[bool] = None
            if session.tipsc:
                tipsc_score = session.tipsc.total_score
                ready_for_dfv = session.tipsc.ready_for_dfv

            items.append(
                MentorSessionListItem(
                    session_id=str(session.id),
                    team_id=session.team_id,
                    team_name=team.team_name if team else None,
                    student_name=student.name if student else None,
                    status=session.status.value if hasattr(session.status, "value") else session.status,
                    tipsc_score=tipsc_score,
                    ready_for_dfv=ready_for_dfv,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                )
            )

        return items, total_sessions

    # ── Session detail ────────────────────────────────────────────────────────

    async def get_supervised_session_detail(
        self,
        session_id: str,
        mentor_team_ids: list[str],
    ) -> Session:
        """
        Return the full session document for a mentor.

        Validates that session.team_id is in the mentor's supervised teams.
        Raises SessionNotFoundError (404) if:
          - session does not exist, OR
          - session exists but belongs to a team the mentor doesn't supervise.
        This prevents mentors from inferring sessions on unassigned teams exist.

        Returns:
            The full Session document (includes tipsc, dfv, discovery outputs).
        """
        session = await session_repo.find_by_id(session_id)

        if session is None:
            raise SessionNotFoundError()

        # Ownership check — does the mentor supervise this session's team?
        if session.team_id not in mentor_team_ids:
            logger.info(
                "Mentor %s tried to access session %s on unassigned team %s",
                "mentor",
                session_id,
                session.team_id,
            )
            # Return 404 not 403 — don't reveal the session exists
            raise SessionNotFoundError()

        return session

    # ── Teams ─────────────────────────────────────────────────────────────────

    async def get_mentor_teams(
        self,
        mentor_id: str,
        mentor_team_ids: list[str],
    ) -> list[MentorTeamResponse]:
        """
        Return full team details for all teams supervised by this mentor.

        For each team:
          - Fetches team document from `teams` collection.
          - Resolves each member's user document for name + SRN.
          - Counts active (non-archived) sessions for the team.

        Mentor with no assigned teams → returns [].

        Returns:
            list of MentorTeamResponse (sorted by team_name).
        """
        if not mentor_team_ids:
            return []

        results: list[MentorTeamResponse] = []

        for team_id in mentor_team_ids:
            try:
                team = await Team.get(PydanticObjectId(team_id))
            except Exception:
                team = None

            if team is None:
                logger.warning(
                    "Mentor %s has team_id %s in mentor_team_ids but team not found in DB",
                    mentor_id,
                    team_id,
                )
                continue

            # Resolve member user docs
            members: list[TeamMemberInfo] = []
            for member_id in team.members:
                try:
                    user = await User.get(PydanticObjectId(member_id))
                    if user:
                        members.append(
                            TeamMemberInfo(
                                user_id=str(user.id),
                                name=user.name,
                                srn=user.srn,
                            )
                        )
                except Exception:
                    pass

            # Count active sessions (non-archived) for this team
            active_count = await session_repo.count_by_teams(
                team_ids=[team_id],
                filters=None,
            )

            results.append(
                MentorTeamResponse(
                    team_id=str(team.id),
                    team_name=team.team_name,
                    member_count=len(team.members),
                    active_session_count=active_count,
                    members=members,
                )
            )

        # Sort alphabetically by team name for deterministic ordering
        results.sort(key=lambda t: t.team_name)
        return results


mentor_service = MentorService()
