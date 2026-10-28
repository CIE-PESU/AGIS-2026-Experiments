"""
api/v1/quickstart.py — Quickstart evaluation endpoint.

Rapid AI evaluation combining Ethics (3 gates), TIPSC (4 dimensions), and DFV (3 pillars)
into a single 10-parameter assessment. Runs in-process via CrewAI agent.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, status
from quickstart_agent.models import ParameterRating, QuickstartInput, QuickstartOutput

from core.constants import UserRole
from dependencies.auth import require_role
from schemas.auth import CurrentUser
from utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/quickstart",
    tags=["Quickstart"],
)


async def run_quickstart_agent(input_data: QuickstartInput) -> QuickstartOutput:
    """Run the quickstart evaluation agent in-process (async)."""
    try:
        # Convert to agent's input model
        agent_input = QuickstartInput(**input_data.model_dump())

        # Run the evaluation (async)
        from quickstart_agent.main import run_quickstart_eval_async

        agent_output = await run_quickstart_eval_async(agent_input)

        # Convert back to API output model
        return QuickstartOutput(
            input=input_data,
            parameters=[ParameterRating(**p.model_dump()) for p in agent_output.parameters],
            red_count=agent_output.red_count,
            yellow_count=agent_output.yellow_count,
            green_count=agent_output.green_count,
            parameter_advice=agent_output.parameter_advice,
            priority_advice=agent_output.priority_advice,
            timestamp=agent_output.timestamp,
        )
    except Exception as e:
        logger.error(f"Quickstart agent failed: {e}")
        raise RuntimeError(f"Quickstart evaluation failed: {e}") from e


@router.post(
    "/evaluate",
    status_code=status.HTTP_200_OK,
    summary="Run quickstart evaluation",
)
async def evaluate_quickstart(
    request: Request,
    current_user: Annotated[
        CurrentUser,
        Depends(require_role(UserRole.STUDENT, UserRole.MENTOR_WORKSPACE, UserRole.ADMIN)),
    ],
    input_data: QuickstartInput = Body(...),
):
    """
    Run rapid AI evaluation on a startup idea.

    Evaluates 10 parameters across Ethics (3), TIPSC (4), and DFV (3) frameworks.
    Returns GREEN/YELLOW/RED ratings with reasons and actionable advice.
    """
    from fastapi import HTTPException

    from core.config import settings

    try:
        result = await asyncio.wait_for(
            run_quickstart_agent(input_data), settings.CREWAI_TIMEOUT_SECONDS
        )
    except TimeoutError as exc:
        raise HTTPException(504, "Quickstart evaluation timed out. Please retry.") from exc
    return success_response(data=result, request=request)
