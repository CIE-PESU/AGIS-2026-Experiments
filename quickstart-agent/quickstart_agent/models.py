from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, get_args
from pydantic import BaseModel, ConfigDict, Field, model_validator


class QuickstartInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    problem: str = Field(..., min_length=1, max_length=5000, description="Core problem being solved")
    customer: str = Field(..., min_length=1, max_length=5000, description="Who experiences this problem")
    solution: str = Field(..., min_length=1, max_length=5000, description="Proposed solution")
    consequence: str = Field(..., min_length=1, max_length=5000, description="What happens if problem unsolved")
    business_model: str = Field(..., min_length=1, max_length=5000, description="How it makes money / who pays")
    urgency: str = Field(..., min_length=1, max_length=5000, description="Why now / timeline")
    hurdles: str = Field(..., min_length=1, max_length=5000, description="Biggest tech/legal/regulatory hurdles")


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
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @model_validator(mode="after")
    def validate_parameter_set(self):
        expected = set(get_args(ParameterRating.model_fields["name"].annotation))
        if len(self.parameters) != len(expected) or {p.name for p in self.parameters} != expected:
            raise ValueError("Quickstart must rate each of its ten parameters exactly once")
        actual = [sum(p.rating == rating for p in self.parameters) for rating in ["RED", "YELLOW", "GREEN"]]
        if actual != [self.red_count, self.yellow_count, self.green_count]:
            raise ValueError("Quickstart counts must match its parameter ratings")
        return self

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