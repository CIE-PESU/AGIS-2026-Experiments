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

    QUEUED = "QUEUED"
    PRE_EVAL = "PRE_EVAL"

    VALIDATION_RUNNING = "VALIDATION_RUNNING"

    REGULATORY_RUNNING = "REGULATORY_RUNNING"

    ETHICS_RUNNING = "ETHICS_RUNNING"

    TIPSC_RUNNING = "TIPSC_RUNNING"

    FOLLOWUP_REQUIRED = "FOLLOWUP_REQUIRED"

    WAITING_FOR_FOUNDER = "WAITING_FOR_FOUNDER"

    TIPSC_REEVALUATION = "TIPSC_REEVALUATION"

    TIPSC_COMPLETE = "TIPSC_COMPLETE"

    READY_FOR_DFV = "READY_FOR_DFV"

    DFV_RUNNING = "DFV_RUNNING"

    DFV_COMPLETE = "DFV_COMPLETE"

    FAILED = "FAILED"


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