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
    target_geography: str
    industry_sector: str

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
        "target_geography",
        "industry_sector",
        mode="before"
    )
    @classmethod
    def fix_strings(cls, v):
        if isinstance(v, list):
            return " ".join(map(str, v))
        return v


class AssumptionCheck(BaseModel):
    assumption: str
    verdict: Literal["CONFIRMED", "UNCONFIRMED", "CONTRADICTED"]
    evidence: str

    @field_validator("verdict", mode="before")
    @classmethod
    def uppercase_verdict(cls, v):
        return v.strip().upper() if isinstance(v, str) else v

    @field_validator("evidence", mode="before")
    @classmethod
    def normalize_evidence(cls, v):
        if v is None:
            return "No evidence found."
        return str(v)


class ValidationOutput(BaseModel):
    target_geography: str
    industry_sector: str
    checked_assumptions: list[AssumptionCheck]
    competitor_landscape: str
    market_notes: str
    validation_summary: Literal["STRONG", "MIXED", "WEAK"]

    @field_validator("validation_summary", mode="before")
    @classmethod
    def uppercase_summary(cls, v):
        return v.strip().upper() if isinstance(v, str) else v


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
    
    @model_validator(mode="after")
    def enforce_aggregation_rules(self) -> "EthicsOutput":
        gates = [self.harm_vector, self.legal_risk, self.problem_solution_integrity]
 
        correct_pass = "RED" not in gates
        if self.ethics_pass != correct_pass:
            print(f"  [Auto-correct] ethics_pass: {self.ethics_pass} -> {correct_pass}")
            self.ethics_pass = correct_pass

        correct_compliance_flag = self.legal_risk == "YELLOW"
        if self.compliance_flag != correct_compliance_flag:
            print(f"  [Auto-correct] compliance_flag: {self.compliance_flag} -> {correct_compliance_flag}")
            self.compliance_flag = correct_compliance_flag

        if not self.ethics_pass and not self.rejection_reason:
            failed_gate = (
                "harm_vector" if self.harm_vector == "RED"
                else "legal_risk" if self.legal_risk == "RED"
                else "problem_solution_integrity"
            )
            self.rejection_reason = f"Blocked: {failed_gate} gate scored RED."
            print(f"  [Auto-correct] rejection_reason was empty on a failing result; filled from {failed_gate}.")
 
        return self


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
    

    # comment this to check without python level for overall readiness 
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
            print(f"  [Auto-correct] overall_readiness: {self.overall_readiness} -> {correct_readiness}")
            self.overall_readiness = correct_readiness

        # Recompute ready_for_dfv using the corrected readiness
        if self.solution_alignment == "RED":
            correct_dfv = False
        elif correct_readiness == "WEAK":
            correct_dfv = False
        else:
            correct_dfv = True

        if self.ready_for_dfv != correct_dfv:
            print(f"  [Auto-correct] ready_for_dfv: {self.ready_for_dfv} -> {correct_dfv}")
            self.ready_for_dfv = correct_dfv

        return self


class ApplicableRegulation(BaseModel):
    name: str
    jurisdiction: str
    compliance_burden: Literal["HIGH", "MEDIUM", "LOW"]
    brief_requirement: str
 
    @field_validator("compliance_burden", mode="before")
    @classmethod
    def uppercase_burden(cls, v):
        return v.strip().upper() if isinstance(v, str) else v
 
 
class RegulatoryOutput(BaseModel):
    target_geography: str
    industry_sector: str
    applicable_regulations: list[ApplicableRegulation] = []
    regulatory_summary: str
    requires_specialist_review: bool
    key_compliance_risks: list[str] = []
 
    @field_validator("applicable_regulations", mode="before")
    @classmethod
    def normalize_regulations(cls, v):
        if not isinstance(v, list):
            return []
        return v
 
    @field_validator("key_compliance_risks", mode="before")
    @classmethod
    def normalize_risks(cls, v):
        if not isinstance(v, list):
            return []
        return [str(r) for r in v]
 
    @field_validator("regulatory_summary", mode="before")
    @classmethod
    def normalize_summary(cls, v):
        if isinstance(v, list):
            return " ".join(str(x) for x in v)
        return str(v) if v else "No regulatory summary available."
 
    @field_validator("target_geography", "industry_sector", mode="before")
    @classmethod
    def fix_strings(cls, v):
        if isinstance(v, list):
            return " ".join(map(str, v))
        return str(v) if v else ""
 



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



