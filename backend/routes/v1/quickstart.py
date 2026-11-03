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
from quickstart_agent.models import QuickstartInput, QuickstartOutput

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
        from quickstart_agent.main import run_quickstart_eval_async

        return await run_quickstart_eval_async(input_data)
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
    except Exception as exc:
        logger.error("Quickstart did not produce a validated result: %s", type(exc).__name__)
        raise HTTPException(
            502,
            "The AI provider did not return a valid evaluation. Check its availability and model configuration; no new result was created.",
        ) from exc
    return success_response(data=result, request=request)
