"""
engine/async_pipeline_executor.py

Async TIPSC pipeline executor.

Flow:
    PreEval
    -> Validation + Regulatory
    -> Ethics
    -> Compliance Context
    -> TIPSC
    -> Optional founder follow-up loop (max 3 turns)
    -> TIPSC completion

MongoDB is the durable source of truth.

The executor never waits for founder input. When a follow-up question is
required, the pipeline stores the question, moves the session to
WAITING_FOR_FOUNDER, and returns.

The pipeline is resumed through resume_after_followup().
"""

from __future__ import annotations

import asyncio
import json
import logging

from datetime import datetime, timezone

from engine.dispatcher import WorkerDispatcher
from engine.state_machine import (
    PipelineContext,
    PipelineState,
)
from tipsc_utils.followup_context import FollowUpContext
from models import PreEvalOutput


logger = logging.getLogger(__name__)


MAX_FOLLOWUP_TURNS = 3


class AsyncPipelineExecutor:

    def __init__(self, stages, db):
        self.stages = stages
        self.dispatcher = WorkerDispatcher(stages)
        self.db = db

    # ──────────────────────────────────────────────────────────────────────
    # Mongo helpers
    # ──────────────────────────────────────────────────────────────────────

    async def _update(
        self,
        session_id: str,
        patch: dict,
    ):
        """
        Persist a partial session update.

        SessionStore owns updated_at generation.
        """

        await self.db.update_session(
            session_id,
            patch,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Fresh pipeline execution
    # ──────────────────────────────────────────────────────────────────────

    async def run(
        self,
        session_id: str,
        preeval_input: dict,
    ):
        """
        Start a fresh TIPSC pipeline.

        Returns when TIPSC either:

        1. Completes
        2. Parks at WAITING_FOR_FOUNDER
        3. Fails
        """

        try:

            session = await self.db.get_session(
                session_id
            )

            if session is None:

                raise ValueError(
                    f"Session not found: {session_id}"
                )

            student_id = session.get("student_id")
            team_id = session.get("team_id")

            logger.info(
                "Starting TIPSC pipeline | "
                "session_id=%s | "
                "student_id=%s | "
                "team_id=%s",
                session_id,
                student_id,
                team_id,
            )

            await self._update(
                session_id,
                {
                    "status": (
                        PipelineState
                        .TIPSC_RUNNING
                        .value
                    ),
                    "error": None,
                    "rejection_reason": None,
                    "preeval_input": (
                        preeval_input.copy()
                    ),
                    "pending_question": None,
                    "pending_answer": None,
                    "followup_turn": 0,
                    "followup_history": [],
                },
            )

            await self._run_internal(
                session_id=session_id,
                preeval_input=preeval_input.copy(),
            )

        except Exception as exc:

            logger.exception(
                "Pipeline failed for session %s",
                session_id,
            )

            dlq_entry = {
                "session_id": session_id,
                "input": preeval_input,
                "error": str(exc),
                "timestamp": (
                    datetime.now(timezone.utc)
                    .isoformat()
                ),
            }

            logger.error(
                "DLQ_ENTRY: %s",
                json.dumps(
                    dlq_entry,
                    default=str,
                ),
            )

            await self._update(
                session_id,
                {
                    "status": (
                        PipelineState
                        .TIPSC_FAILED
                        .value
                    ),
                    "error": str(exc),
                },
            )

    async def _run_internal(
        self,
        session_id: str,
        preeval_input: dict,
    ):
        """
        Execute the initial TIPSC pipeline.
        """

        context = PipelineContext(
            state=PipelineState.PRE_EVAL
        )

        session = await self.db.get_session(
            session_id
        )

        if session is None:

            raise ValueError(
                f"Session not found: {session_id}"
            )

        # ──────────────────────────────────────────────────────────────────
        # PRE-EVALUATION
        # ──────────────────────────────────────────────────────────────────

        logger.info(
            "TIPSC PreEval started | session_id=%s",
            session_id,
        )

        await self._update(
            session_id,
            {
                "status": (
                    PipelineState
                    .PRE_EVAL
                    .value
                ),
            },
        )

        context.preeval = (
            await self.dispatcher.dispatch_preeval(
                preeval_input
            )
        )

        await self._update(
            session_id,
            {
                "preeval": (
                    context.preeval.model_dump()
                ),
            },
        )

        # ──────────────────────────────────────────────────────────────────
        # VALIDATION + REGULATORY
        # ──────────────────────────────────────────────────────────────────

        await self._update(
            session_id,
            {
                "status": (
                    PipelineState
                    .VALIDATION_RUNNING
                    .value
                ),
            },
        )

        (
            context.validation,
            context.regulatory,
        ) = await asyncio.gather(
            self.dispatcher.dispatch_validation(
                context.preeval
            ),
            self.dispatcher.dispatch_regulatory(
                context.preeval
            ),
        )

        validation_context = (
            context.validation.model_dump_json(
                indent=2
            )
        )

        regulatory_context = (
            context.regulatory.model_dump_json(
                indent=2
            )
        )

        await self._update(
            session_id,
            {
                "validation": (
                    context.validation.model_dump()
                ),
                "regulatory": (
                    context.regulatory.model_dump()
                ),
                "status": (
                    PipelineState
                    .ETHICS_RUNNING
                    .value
                ),
            },
        )

        # ──────────────────────────────────────────────────────────────────
        # ETHICS GATE
        # ──────────────────────────────────────────────────────────────────

        context.ethics = (
            await self.dispatcher.dispatch_ethics(
                context.preeval,
                validation_context,
                regulatory_context,
            )
        )

        await self._update(
            session_id,
            {
                "ethics": (
                    context.ethics.model_dump()
                ),
            },
        )

        if not context.ethics.ethics_pass:

            logger.warning(
                "TIPSC ethics gate rejected session | "
                "session_id=%s | reason=%s",
                session_id,
                context.ethics.rejection_reason,
            )

            await self._update(
                session_id,
                {
                    "status": (
                        PipelineState
                        .TIPSC_FAILED
                        .value
                    ),
                    "rejection_reason": (
                        context.ethics
                        .rejection_reason
                    ),
                    "error": None,
                },
            )

            return

        # ──────────────────────────────────────────────────────────────────
        # COMPLIANCE CONTEXT
        # ──────────────────────────────────────────────────────────────────

        context.compliance_context = (
            self.stages.execute_compliance_context(
                context.ethics,
                context.regulatory,
            )
        )

        await self._update(
            session_id,
            {
                "compliance_context": (
                    context.compliance_context
                ),
            },
        )

        # ──────────────────────────────────────────────────────────────────
        # INITIAL TIPSC EVALUATION
        # ──────────────────────────────────────────────────────────────────

        await self._update(
            session_id,
            {
                "status": (
                    PipelineState
                    .TIPSC_RUNNING
                    .value
                ),
            },
        )

        context.tipsc = (
            await self.dispatcher.dispatch_tipsc(
                context.preeval,
                validation_context,
                context.compliance_context,
            )
        )

        tipsc_dump = self._build_tipsc_dump(
            tipsc=context.tipsc,
            compliance_context=(
                context.compliance_context
            ),
            compliance_flag=(
                context.ethics.compliance_flag
            ),
            followups_asked=0,
        )

        await self._update(
            session_id,
            {
                "tipsc": tipsc_dump,
            },
        )

        # ──────────────────────────────────────────────────────────────────
        # FOLLOW-UP DECISION
        # ──────────────────────────────────────────────────────────────────

        if not context.tipsc.needs_followup:

            await self._complete_tipsc(
                session_id=session_id,
                tipsc_dump=tipsc_dump,
                followups_asked=0,
            )

            return

        # Generate Q1 and park.
        await self._generate_and_park_question(
            session_id=session_id,
            tipsc=context.tipsc,
            followup_history=[],
            compliance_context=(
                context.compliance_context
            ),
            turn=1,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Follow-up resume
    # ──────────────────────────────────────────────────────────────────────

    async def resume_after_followup(
        self,
        session_id: str,
        answer: str,
    ):
        """
        Resume a parked TIPSC session.

        All execution context is reconstructed from MongoDB.
        """

        try:

            await self._resume_internal(
                session_id=session_id,
                answer=answer,
            )

        except Exception as exc:

            logger.exception(
                "Follow-up resume failed for session %s",
                session_id,
            )

            await self._update(
                session_id,
                {
                    "status": (
                        PipelineState
                        .TIPSC_FAILED
                        .value
                    ),
                    "error": str(exc),
                },
            )

    async def _resume_internal(
        self,
        session_id: str,
        answer: str,
    ):
        """
        Persist founder answer and re-evaluate TIPSC.
        """

        from tipsc_utils.followup_context import FollowUpContext

        # ──────────────────────────────────────────────────────────────────
        # LOAD SESSION
        # ──────────────────────────────────────────────────────────────────

        session = await self.db.get_session(
            session_id
        )

        if session is None:

            raise ValueError(
                f"Session {session_id} not found in MongoDB"
            )

        current_status = session.get("status")

        if (
            current_status
            != PipelineState
            .WAITING_FOR_FOUNDER
            .value
        ):

            raise ValueError(
                f"Session {session_id} is not waiting "
                f"for founder input "
                f"(current status={current_status})"
            )

        # ──────────────────────────────────────────────────────────────────
        # RECONSTRUCT PIPELINE STATE
        # ──────────────────────────────────────────────────────────────────

        preeval_data = session.get("preeval")

        if not preeval_data:

            raise ValueError(
                f"Session {session_id} has no "
                "persisted preeval output"
            )

        validation_data = session.get(
            "validation"
        )

        if not validation_data:

            raise ValueError(
                f"Session {session_id} has no "
                "persisted validation output"
            )

        pending_question = session.get(
            "pending_question"
        )

        if not pending_question:

            raise ValueError(
                f"Session {session_id} has no "
                "pending follow-up question"
            )

        preeval = PreEvalOutput.model_validate(
            preeval_data
        )

        validation_context = json.dumps(
            validation_data,
            indent=2,
            default=str,
        )

        compliance_context = session.get(
            "compliance_context",
            "",
        )

        turn = int(
            session.get("followup_turn", 1)
            or 1
        )

        if turn < 1 or turn > MAX_FOLLOWUP_TURNS:

            raise ValueError(
                f"Invalid follow-up turn: {turn}"
            )

        followup_history = list(
            session.get(
                "followup_history",
                [],
            )
        )

        # ──────────────────────────────────────────────────────────────────
        # STORE ANSWER
        # ──────────────────────────────────────────────────────────────────

        clean_answer = answer.strip()

        if not clean_answer:

            raise ValueError(
                "Follow-up answer cannot be empty."
            )

        await self._update(
            session_id,
            {
                "pending_answer": clean_answer,
                "status": (
                    PipelineState
                    .TIPSC_REEVALUATION
                    .value
                ),
            },
        )

        exchange = {
            "question": pending_question,
            "answer": clean_answer,
            "turn": turn,
            "answered_at": (
                datetime.now(timezone.utc)
                .isoformat()
            ),
        }

        followup_history.append(exchange)

        # ──────────────────────────────────────────────────────────────────
        # BUILD FOLLOW-UP CONTEXT
        # ──────────────────────────────────────────────────────────────────

        conversation = FollowUpContext()

        for history_item in followup_history:

            conversation.add(
                history_item["question"],
                history_item["answer"],
            )

        followup_context = conversation.build()

        await self._update(
            session_id,
            {
                "followup_history": followup_history,
                "pending_question": None,
                "pending_answer": None,
            },
        )

        logger.info(
            "TIPSC reevaluation started | "
            "session_id=%s | turn=%s",
            session_id,
            turn,
        )

        # ──────────────────────────────────────────────────────────────────
        # TIPSC RE-EVALUATION
        # ──────────────────────────────────────────────────────────────────

        tipsc = (
            await self.dispatcher
            .dispatch_tipsc_reeval(
                preeval,
                validation_context=(
                    validation_context
                ),
                compliance_context=(
                    compliance_context
                ),
                followup_context=(
                    followup_context
                ),
            )
        )

        ethics = session.get("ethics") or {}

        tipsc_dump = self._build_tipsc_dump(
            tipsc=tipsc,
            compliance_context=(
                compliance_context
            ),
            compliance_flag=bool(
                ethics.get(
                    "compliance_flag",
                    False,
                )
            ),
            followups_asked=len(
                followup_history
            ),
        )

        await self._update(
            session_id,
            {
                "tipsc": tipsc_dump,
            },
        )

        # ──────────────────────────────────────────────────────────────────
        # NEXT FOLLOW-UP DECISION
        # ──────────────────────────────────────────────────────────────────

        if (
            tipsc.needs_followup
            and turn < MAX_FOLLOWUP_TURNS
        ):

            await self._generate_and_park_question(
                session_id=session_id,
                tipsc=tipsc,
                followup_history=followup_history,
                compliance_context=(
                    compliance_context
                ),
                turn=turn + 1,
            )

            return

        # Max turns reached or criteria resolved.
        await self._complete_tipsc(
            session_id=session_id,
            tipsc_dump=tipsc_dump,
            followups_asked=len(
                followup_history
            ),
        )

    # ──────────────────────────────────────────────────────────────────────
    # Follow-up generation
    # ──────────────────────────────────────────────────────────────────────

    async def _generate_and_park_question(
        self,
        session_id: str,
        tipsc,
        followup_history: list,
        compliance_context: str,
        turn: int,
    ):
        """
        Generate exactly one founder follow-up question.
        """

        from tipsc_utils.followup_context import FollowUpContext

        if turn > MAX_FOLLOWUP_TURNS:

            raise ValueError(
                "Follow-up turn exceeds maximum."
            )

        conversation = FollowUpContext()

        for exchange in followup_history:

            conversation.add(
                exchange["question"],
                exchange["answer"],
            )

        followup_context = conversation.build()

        followup = (
            await self.dispatcher.dispatch_followup(
                tipsc,
                followup_context=(
                    followup_context
                ),
                compliance_context=(
                    compliance_context
                ),
            )
        )

        # Agent says no question is required.
        if (
            not followup.needs_followup
            or not followup.questions
        ):

            session = await self.db.get_session(
                session_id
            )

            tipsc_dump = (
                session.get("tipsc", {})
                if session
                else {}
            )

            await self._complete_tipsc(
                session_id=session_id,
                tipsc_dump=tipsc_dump,
                followups_asked=len(
                    followup_history
                ),
            )

            return

        # Ask one question per turn.
        question = str(
            followup.questions[0]
        ).strip()

        if not question:

            raise ValueError(
                "Follow-up agent generated an empty question."
            )

        await self._update(
            session_id,
            {
                "status": (
                    PipelineState
                    .WAITING_FOR_FOUNDER
                    .value
                ),
                "pending_question": question,
                "pending_answer": None,
                "followup_turn": turn,
                "followup_history": followup_history,
                "error": None,
            },
        )

        logger.info(
            "Session %s parked at "
            "WAITING_FOR_FOUNDER "
            "(turn %s/%s) | question=%s",
            session_id,
            turn,
            MAX_FOLLOWUP_TURNS,
            question,
        )

    # ──────────────────────────────────────────────────────────────────────
    # TIPSC dump helper
    # ──────────────────────────────────────────────────────────────────────

    def _build_tipsc_dump(
        self,
        tipsc,
        compliance_context: str,
        compliance_flag: bool,
        followups_asked: int,
    ) -> dict:
        """
        Normalize TIPSC output for backend MongoDB storage.
        """

        tipsc_dump = tipsc.model_dump()

        tipsc_dump["reasoning"] = (
            compliance_context[:500]
            if compliance_context
            else ""
        )

        tipsc_dump["compliance_flag"] = (
            compliance_flag
        )

        tipsc_dump["followups_asked"] = (
            followups_asked
        )

        tipsc_dump["completed_at"] = None

        return tipsc_dump

    # ──────────────────────────────────────────────────────────────────────
    # TIPSC completion
    # ──────────────────────────────────────────────────────────────────────

    async def _complete_tipsc(
        self,
        session_id: str,
        tipsc_dump: dict,
        followups_asked: int,
    ):
        """
        Finalize TIPSC and clear transient follow-up state.
        """

        final_tipsc = dict(
            tipsc_dump
        )

        final_tipsc["followups_asked"] = (
            followups_asked
        )

        final_tipsc["completed_at"] = (
            datetime.now(timezone.utc)
        )

        # The follow-up lifecycle has ended.
        final_tipsc["needs_followup"] = False

        await self._update(
            session_id,
            {
                "status": (
                    PipelineState
                    .TIPSC_COMPLETED
                    .value
                ),
                "tipsc": final_tipsc,
                "pending_question": None,
                "pending_answer": None,
                "followup_turn": 0,
                "error": None,
            },
        )

        logger.info(
            "TIPSC completed | "
            "session_id=%s | "
            "followups_asked=%s | "
            "ready_for_dfv=%s",
            session_id,
            followups_asked,
            final_tipsc.get(
                "ready_for_dfv"
            ),
        )