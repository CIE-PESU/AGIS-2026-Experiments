from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class QuickstartInput(BaseModel):
    problem: str = Field(..., description="Core problem being solved")
    customer: str = Field(..., description="Who experiences this problem")
    solution: str = Field(..., description="Proposed solution")
    consequence: str = Field(..., description="What happens if problem unsolved")
    business_model: str = Field(..., description="How it makes money / who pays")
    urgency: str = Field(..., description="Why now / timeline")
    hurdles: str = Field(..., description="Biggest tech/legal/regulatory hurdles")


class ParameterRating(BaseModel):
    name: Literal[
        "harm_vector",
        "legal_risk",
        "problem_solution_integrity",
        "timely",
        "important",
        "profitable",
        "solvable",
        "desirability",
        "feasibility",
        "viability",
    ]
    rating: Literal["GREEN", "YELLOW", "RED"]
    reason: str


class QuickstartOutput(BaseModel):
    input: QuickstartInput
    parameters: list[ParameterRating]
    red_count: int
    yellow_count: int
    green_count: int
    parameter_advice: dict[str, str]
    priority_advice: list[str]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    @classmethod
    def from_raw(cls, input_data: QuickstartInput, raw_params: list[dict], advice: dict, priority: list[str]) -> "QuickstartOutput":
        params = [ParameterRating(**p) for p in raw_params]
        red = sum(1 for p in params if p.rating == "RED")
        yellow = sum(1 for p in params if p.rating == "YELLOW")
        green = sum(1 for p in params if p.rating == "GREEN")
        return cls(
            input=input_data,
            parameters=params,
            red_count=red,
            yellow_count=yellow,
            green_count=green,
            parameter_advice=advice,
            priority_advice=priority,
        )