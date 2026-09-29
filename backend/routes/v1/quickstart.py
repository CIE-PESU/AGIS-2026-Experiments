"""
api/v1/quickstart.py — Quickstart evaluation endpoint.

Rapid AI evaluation combining Ethics (3 gates), TIPSC (4 dimensions), and DFV (3 pillars)
into a single 10-parameter assessment. Runs in-process via CrewAI agent.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, status
from pydantic import BaseModel, Field
from core.constants import UserRole
from dependencies.auth import require_role
from schemas.auth import CurrentUser
from utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/quickstart",
    tags=["Quickstart"],
)


class QuickstartInput(BaseModel):
    problem: str = Field(..., description="Core problem being solved")
    customer: str = Field(..., description="Who experiences this problem")
    solution: str = Field(..., description="Proposed solution")
    consequence: str = Field(..., description="What happens if problem unsolved")
    business_model: str = Field(..., description="How it makes money / who pays")
    urgency: str = Field(..., description="Why now / timeline")
    hurdles: str = Field(..., description="Biggest tech/legal/regulatory hurdles")


class ParameterRating(BaseModel):
    name: str
    rating: str
    reason: str


class QuickstartOutput(BaseModel):
    input: QuickstartInput
    parameters: list[ParameterRating]
    red_count: int
    yellow_count: int
    green_count: int
    parameter_advice: dict[str, str]
    priority_advice: list[str]
    timestamp: str


# =============================================================================
# Agent Loading (same pattern as DFV/Discovery agents in combined_agent_worker)
# =============================================================================

BACKEND_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

PROJECT_ROOT = os.path.abspath(
    os.path.join(BACKEND_ROOT, "..")
)

def _load_module(module_name: str, module_path: str):
    """Load a module from a specific file path."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_quickstart_agent():
    """Load the quickstart agent dynamically from project root."""
    quickstart_agent_dir = os.path.join(
        PROJECT_ROOT,
        "quickstart-agent",
    )
    quickstart_path = os.path.join(
        quickstart_agent_dir,
        "quickstart_agent",
        "main.py",
    )

    # Add quickstart-agent to sys.path so relative imports work
    if quickstart_agent_dir not in sys.path:
        sys.path.insert(0, quickstart_agent_dir)

    try:
        module = _load_module(
            "agis_quickstart_agent_main",
            quickstart_path,
        )

        logger.info(
            "Quickstart agent loaded from %s",
            quickstart_path,
        )

        return module.run_quickstart_eval

    except Exception:
        logger.exception(
            "Failed to load Quickstart agent"
        )
        raise


# Load agent before restoring backend models
run_quickstart_eval = _load_quickstart_agent()

# Import agent models after loading
from quickstart_agent.models import QuickstartInput as AgentInput, QuickstartOutput as AgentOutput


async def run_quickstart_agent(input_data: QuickstartInput) -> QuickstartOutput:
    """Run the quickstart evaluation agent in-process (async)."""
    try:
        # Convert to agent's input model
        agent_input = AgentInput(**input_data.model_dump())

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
        raise RuntimeError(f"Quickstart evaluation failed: {e}")


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
    result = await run_quickstart_agent(input_data)
    return success_response(data=result, request=request)