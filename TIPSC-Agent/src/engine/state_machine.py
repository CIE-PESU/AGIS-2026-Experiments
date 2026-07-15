"""
engine/state_machine.py

Internal TIPSC pipeline execution state.

IMPORTANT:
These values are persisted directly into the backend MongoDB sessions
collection. Therefore persisted values MUST match backend SessionStatus
string values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from models import (
    EthicsOutput,
    PreEvalOutput,
    RegulatoryOutput,
    TIPSCOutput,
    ValidationOutput,
)


class PipelineState(str, Enum):
    """
    TIPSC pipeline execution states.

    Internal progress states may exist here even when they are not part of
    the backend transition validator. Their string values are persisted to
    MongoDB and exposed to the frontend.
    """

    QUEUED = "queued"

    PRE_EVAL = "pre_eval"

    VALIDATION_RUNNING = "validation_running"

    REGULATORY_RUNNING = "regulatory_running"

    ETHICS_RUNNING = "ethics_running"

    TIPSC_RUNNING = "tipsc_running"

    TIPSC_REEVALUATION = "tipsc_reevaluation"

    WAITING_FOR_FOUNDER = "waiting_for_founder"

    TIPSC_COMPLETED = "tipsc_completed"

    TIPSC_FAILED = "tipsc_failed"


@dataclass
class PipelineContext:
    """
    In-memory context for one TIPSC execution.

    MongoDB remains the durable source of truth. This object only carries
    state while one executor invocation is active.
    """

    state: PipelineState = PipelineState.QUEUED

    preeval: Optional[PreEvalOutput] = None

    validation: Optional[ValidationOutput] = None

    regulatory: Optional[RegulatoryOutput] = None

    ethics: Optional[EthicsOutput] = None

    tipsc: Optional[TIPSCOutput] = None

    compliance_context: str = ""

    followup_context: str = ""