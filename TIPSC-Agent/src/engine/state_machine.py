from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

from models import (
    PreEvalOutput,
    ValidationOutput,
    RegulatoryOutput,
    EthicsOutput,
    TIPSCOutput,
)

class PipelineState(str, Enum):
    """
    Pipeline state values. MUST match backend/state_machine/states.py SessionStatus
    exactly (same lowercase strings) so that MongoDB queries work across both systems.
    """
    QUEUED              = "queued"
    PRE_EVAL            = "pre_eval"
    VALIDATION_RUNNING  = "validation_running"
    ETHICS_RUNNING      = "ethics_running"
    TIPSC_RUNNING       = "tipsc_running"
    TIPSC_REEVALUATION  = "tipsc_reevaluation"
    WAITING_FOR_FOUNDER = "waiting_for_founder"
    TIPSC_COMPLETE      = "tipsc_completed"   # matches SessionStatus.TIPSC_COMPLETED
    FAILED              = "failed"


@dataclass
class PipelineContext:

    state: PipelineState

    preeval: Optional[PreEvalOutput] = None
    validation: Optional[ValidationOutput] = None
    regulatory: Optional[RegulatoryOutput] = None
    ethics: Optional[EthicsOutput] = None
    tipsc: Optional[TIPSCOutput] = None

    compliance_context: str = ""
    followup_context: str = ""