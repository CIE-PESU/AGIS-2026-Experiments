import asyncio
import json 
import logging
from datetime import datetime

from engine.dispatcher import WorkerDispatcher
from engine.state_machine import PipelineContext, PipelineState
from models import PreEvalOutput

logger = logging.getLogger(__name__)

MAX_FOLLOWUP_TURNS = 3


class AsyncPipelineExecutor:

    def __init__(self, stages, db):
        self.stages = stages
        self.dispatcher = WorkerDispatcher(stages)
        self.db = db

    async def _update(self, session_id: str, patch: dict):
        patch["updated_at"] = datetime.utcnow().isoformat()
        await self.db.update_session(session_id, patch)

    async def run(self, session_id: str, preeval_input: dict):
        """
        Start a fresh pipeline run.  Runs synchronously through PreEval →
        Validation/Regulatory (parallel) → Ethics → TIPSC.
 
        If TIPSC decides needs_followup=True, generates the first question,
        writes it to MongoDB as WAITING_FOR_FOUNDER, and RETURNS immediately.
        The pipeline is now parked — no polling, no held-open coroutine.
 
        Resumption happens via resume_after_followup() when the founder
        submits an answer through the API.
        """
        try:
            await self._run_internal(session_id, preeval_input)
        except Exception as e:
            logger.exception(f"Pipeline failed for session {session_id}")
            await self._update(session_id, {
                "state": PipelineState.FAILED,
                "error": str(e),
            })


    async def _run_internal(self, session_id: str, preeval_input: dict):
        context = PipelineContext(state=PipelineState.PRE_EVAL)

        team_id = preeval_input.pop("team_id", None)
        student_id = preeval_input.pop("student_id", None)

        await self._update(session_id, {
            "state": PipelineState.PRE_EVAL,
            "team_id": team_id,
            "student_id": student_id,
        })

        context.preeval = await self.dispatcher.dispatch_preeval(preeval_input)
        await self._update(session_id, {
            "preeval": context.preeval.model_dump(),
        })

        await self._update(session_id, {"state": PipelineState.VALIDATION_RUNNING})

        context.validation, context.regulatory = await asyncio.gather(
            self.dispatcher.dispatch_validation(context.preeval),
            self.dispatcher.dispatch_regulatory(context.preeval),
        )

        validation_context = context.validation.model_dump_json(indent=2)
        regulatory_context = context.regulatory.model_dump_json(indent=2)

        await self._update(session_id, {
            "state": PipelineState.ETHICS_RUNNING,
            "validation": context.validation.model_dump(),
            "regulatory": context.regulatory.model_dump(),
        })

        context.ethics = await self.dispatcher.dispatch_ethics(
            context.preeval, validation_context, regulatory_context,
        )

        if not context.ethics.ethics_pass:
            await self._update(session_id, {
                "state": PipelineState.FAILED,
                "ethics": context.ethics.model_dump(),
                "rejection_reason": context.ethics.rejection_reason,
            })
            return

        context.compliance_context = self.stages.execute_compliance_context(
            context.ethics, context.regulatory,
        )

        await self._update(session_id, {
            "ethics": context.ethics.model_dump(),
            "compliance_context": context.compliance_context,
        })

        await self._update(session_id, {"state": PipelineState.TIPSC_RUNNING})

        context.tipsc = await self.dispatcher.dispatch_tipsc(
            context.preeval, validation_context, context.compliance_context,
        )

        await self._update(session_id, {"tipsc": context.tipsc.model_dump()})

        if not context.tipsc.needs_followup:
            await self._update(session_id, {"state": PipelineState.TIPSC_COMPLETE})
            return
        
        # ── Followup: generate Q1 and park ───────────────────────────────────
        # Pipeline stops here.  Continues via resume_after_followup() when
        # the founder submits an answer.
        await self._generate_and_park_question(
            session_id=session_id,
            tipsc=context.tipsc,
            followup_history=[],       # no exchanges yet
            compliance_context=context.compliance_context,
            turn=1,
        )

     # ── Entry point: resume after founder answer ──────────────────────────────
 
    async def resume_after_followup(self, session_id: str, answer: str):
        """
        Called by the FastAPI /followup endpoint (as a background task) when
        the founder submits an answer.
 
        Fetches ALL context from MongoDB — no in-memory state is assumed.
        This makes the pipeline fully resumable: the user can answer hours,
        days, or weeks later and the computation picks up correctly.
 
        Flow:
          1. Fetch session from MongoDB.
          2. Reconstruct preeval, validation_context, compliance_context,
             followup_history from persisted fields.
          3. Append the new (question, answer) exchange.
          4. Run TIPSC reeval.
          5a. If needs_followup and turn < MAX → generate next question, park.
          5b. Otherwise → TIPSC_COMPLETE.
        """
        try:
            await self._resume_internal(session_id, answer)
        except Exception as e:
            logger.exception(f"Followup resume failed for session {session_id}")
            await self._update(session_id, {
                "state": PipelineState.FAILED,
                "error": str(e),
            })

    async def _resume_internal(self, session_id: str, answer: str):
        from utils.followup_context import FollowUpContext
 
        # ── Fetch session ─────────────────────────────────────────────────────
        session = await self.db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found in MongoDB")
 
        if session.get("state") != PipelineState.WAITING_FOR_FOUNDER:
            raise ValueError(
                f"Session {session_id} is not waiting for a founder answer "
                f"(current state={session.get('state')})"
            )
        
        # ── Reconstruct context from MongoDB ──────────────────────────────────
        # These were persisted during the original run() call.
        # No in-memory pipeline objects are needed.
        preeval = PreEvalOutput.model_validate(session["preeval"])
        validation_context = json.dumps(session["validation"], indent=2)
        compliance_context = session.get("compliance_context", "")
        turn = session.get("followup_turn", 1)
        question = session["pending_question"]
 
        # ── Append new answer to persisted history ────────────────────────────
        followup_history = session.get("followup_history", [])
        followup_history.append({"question": question, "answer": answer})
 
        # Rebuild FollowUpContext from the full history so the agent sees
        # all prior Q&A in its formatted prompt.
        conversation = FollowUpContext()
        for exchange in followup_history:
            conversation.add(exchange["question"], exchange["answer"])
        followup_ctx_str = conversation.build()
 
        # ── TIPSC Reeval ──────────────────────────────────────────────────────
        await self._update(session_id, {
            "state": PipelineState.TIPSC_REEVALUATION,
            "followup_history": followup_history,
        })
 
        tipsc = await self.dispatcher.dispatch_tipsc_reeval(
            preeval,
            validation_context=validation_context,
            compliance_context=compliance_context,
            followup_context=followup_ctx_str,
        )
 
        await self._update(session_id, {"tipsc": tipsc.model_dump()})
 
        # ── Decide next step ──────────────────────────────────────────────────
        if tipsc.needs_followup and turn < MAX_FOLLOWUP_TURNS:
            # Still gaps and budget remaining — generate next question and park.
            await self._generate_and_park_question(
                session_id=session_id,
                tipsc=tipsc,
                followup_history=followup_history,
                compliance_context=compliance_context,
                turn=turn + 1,
            )
        else:
            # Either all dimensions resolved, or we've hit the turn cap.
            await self._update(session_id, {"state": PipelineState.TIPSC_COMPLETE})
 


    # ── Shared helper: generate a question and park at WAITING_FOR_FOUNDER ───
 
    async def _generate_and_park_question(
        self,
        session_id: str,
        tipsc,
        followup_history: list,
        compliance_context: str,
        turn: int,
    ):
        """
        Ask the followup agent for the next question given the current TIPSC
        output and conversation history, then write it to MongoDB as
        WAITING_FOR_FOUNDER.
 
        Used on the initial TIPSC → followup transition AND on every
        subsequent turn inside resume_after_followup().
        """
        from utils.followup_context import FollowUpContext
 
        # Rebuild conversation so the followup agent sees prior Q&A.
        conversation = FollowUpContext()
        for exchange in followup_history:
            conversation.add(exchange["question"], exchange["answer"])
        followup_ctx_str = conversation.build()
 
        followup = await self.dispatcher.dispatch_followup(
            tipsc,
            followup_context=followup_ctx_str,
            compliance_context=compliance_context,
        )
 
        if not followup.needs_followup or not followup.questions:
            # Followup agent says no more questions needed.
            await self._update(session_id, {"state": PipelineState.TIPSC_COMPLETE})
            return
 
        question = followup.questions[0]
 
        # Park the pipeline. Everything needed to resume is in MongoDB:
        #   preeval, validation, regulatory, compliance_context,
        #   followup_history (answers so far), followup_turn, pending_question.
        await self._update(session_id, {
            "state": PipelineState.WAITING_FOR_FOUNDER,
            "pending_question": question,
            "followup_turn": turn,
            "followup_history": followup_history,  # answers so far (pending Q not included)
        })
        logger.info(
            f"Session {session_id} parked at WAITING_FOR_FOUNDER "
            f"(turn {turn}/{MAX_FOLLOWUP_TURNS})"
        )
 