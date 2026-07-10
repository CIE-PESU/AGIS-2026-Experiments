from dataclasses import dataclass
from typing import List


@dataclass
class EvidenceChange:

    criterion: str
    previous_state: str
    current_state: str
    reason: str


class ReEvaluationTracker:

    def __init__(self):

        self.changes: List[EvidenceChange] = []

    def add_change(
        self,
        criterion,
        previous,
        current,
        reason,
    ):

        self.changes.append(
            EvidenceChange(
                criterion,
                previous,
                current,
                reason,
            )
        )

    def build_summary(self):

        if not self.changes:

            return "No evidence changes detected."

        output = []

        output.append("RE-EVALUATION SUMMARY")
        output.append("=" * 50)

        for change in self.changes:

            output.append(
                f"""
Criterion:
{change.criterion}

Previous:
{change.previous_state}

Current:
{change.current_state}

Reason:
{change.reason}
"""
            )

        return "\n".join(output)