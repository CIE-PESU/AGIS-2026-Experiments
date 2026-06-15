from pydantic import BaseModel, field_validator, model_validator
from typing import Literal

class RefinedIdea(BaseModel):
    customer_segment: str
    qualified_problem: str
    consequence: str
    proposed_solution: str


class TIPSValidatedMetrics(BaseModel):
    timely_factor: str
    importance_metric: str
    profitability_pivot: str
    solvability_constraint: str


class TIPSRAGScores(BaseModel):
    T: Literal["GREEN", "YELLOW", "RED"]
    I: Literal["GREEN", "YELLOW", "RED"]
    P: Literal["GREEN", "YELLOW", "RED"]
    S: Literal["GREEN", "YELLOW", "RED"]

    @field_validator("T", "I", "P", "S", mode="before")
    @classmethod
    def uppercase_scores(cls, v):
        return v.strip().upper() if isinstance(v, str) else v


class PreEvalOutput(BaseModel):
    problem_statement: str
    customer_segment: str
    consequence: str
    assumptions: list[str]
    proposed_solution: str

    @field_validator("assumptions", mode="before")
    @classmethod
    def fix_assumptions(cls, v):
        if isinstance(v, str):
            return [v]
        return v

    @field_validator(
        "problem_statement",
        "customer_segment",
        "consequence",
        "proposed_solution",
        mode="before"
    )
    @classmethod
    def fix_strings(cls, v):
        if isinstance(v, list):
            return " ".join(map(str, v))
        return v


class EthicsOutput(BaseModel):
    harm_vector: Literal["GREEN", "YELLOW", "RED"]
    harm_reason: str
    legal_risk: Literal["GREEN", "YELLOW", "RED"]
    legal_reason: str
    problem_solution_integrity: Literal["GREEN", "RED"]
    integrity_reason: str
    ethics_pass: bool
    compliance_flag: bool
    rejection_reason: str  # empty string when ethics_pass is True
 
    @field_validator(
        "harm_vector",
        "legal_risk",
        "problem_solution_integrity",
        mode="before",
    )
    @classmethod
    def uppercase_scores(cls, v):
        return v.strip().upper() if isinstance(v, str) else v
 
    @field_validator("rejection_reason", mode="before")
    @classmethod
    def normalize_rejection(cls, v):
        if v is None:
            return ""
        return str(v)
 


class TIPSCOutput(BaseModel):
    refined_idea: RefinedIdea

    solution_alignment: Literal[
        "GREEN",
        "YELLOW",
        "RED"
    ]

    tips_validated_metrics: TIPSValidatedMetrics

    tips_rag_scores: TIPSRAGScores

    overall_readiness: Literal[
        "STRONG",
        "MODERATE",
        "WEAK"
    ]

    ready_for_dfv: bool

    @field_validator("solution_alignment", "overall_readiness", mode="before")
    @classmethod
    def uppercase_literals(cls, v):
        return v.strip().upper() if isinstance(v, str) else v
    
    @model_validator(mode="after")                          # ← ADD THIS
    def enforce_aggregation_rules(self) -> "TIPSCOutput":
        scores = [
            self.tips_rag_scores.T,
            self.tips_rag_scores.I,
            self.tips_rag_scores.P,
            self.tips_rag_scores.S,
        ]

        # Recompute overall_readiness
        if "RED" in scores:
            correct_readiness = "WEAK"
        elif scores.count("GREEN") >= 3:
            correct_readiness = "STRONG"
        else:
            correct_readiness = "MODERATE"

        if self.overall_readiness != correct_readiness:
            print(f"  [Auto-correct] overall_readiness: {self.overall_readiness} → {correct_readiness}")
            self.overall_readiness = correct_readiness

        # Recompute ready_for_dfv using the corrected readiness
        if self.solution_alignment == "RED":
            correct_dfv = False
        elif correct_readiness == "WEAK":
            correct_dfv = False
        else:
            correct_dfv = True

        if self.ready_for_dfv != correct_dfv:
            print(f"  [Auto-correct] ready_for_dfv: {self.ready_for_dfv} → {correct_dfv}")
            self.ready_for_dfv = correct_dfv

        return self



class FollowUpOutput(BaseModel):
    needs_followup: bool
    questions: list[str] = []

    @field_validator("questions", mode="before")
    @classmethod
    def normalize_questions(cls, v):
        if not isinstance(v, list):
            return []
        normalized = []
        for item in v:
            if isinstance(item, str):
                normalized.append(item)
            elif isinstance(item, dict):
                # Handle {"question": "..."} or {"text": "..."} or {"q": "..."}
                for key in ("question", "text", "q", "content"):
                    if key in item:
                        normalized.append(str(item[key]))
                        break
                else:
                    # Fallback: join all values
                    normalized.append(" ".join(str(v) for v in item.values()))
        return normalized



