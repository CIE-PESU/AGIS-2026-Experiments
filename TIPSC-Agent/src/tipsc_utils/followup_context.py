from dataclasses import dataclass, field
from typing import List


@dataclass
class FollowUpExchange:
    question: str
    answer: str


@dataclass
class FollowUpContext:
    """
    Stores and formats the follow-up conversation
    between the founder and the TIPSC system.
    """

    exchanges: List[FollowUpExchange] = field(default_factory=list)

    def add(self, question: str, answer: str):
        self.exchanges.append(
            FollowUpExchange(
                question=question.strip(),
                answer=answer.strip(),
            )
        )

    def build(self) -> str:

        if not self.exchanges:
            return "No previous follow-up conversation."

        output = []

        output.append("FOLLOW-UP HISTORY")
        output.append("=" * 60)

        for i, exchange in enumerate(self.exchanges, start=1):

            output.append(f"\nQuestion {i}:")
            output.append(exchange.question)

            output.append("\nFounder Response:")
            output.append(exchange.answer)

            output.append("\n")

        output.append("=" * 60)

        output.append("\nQUESTIONS ALREADY ASKED:")

        for exchange in self.exchanges:
            output.append(f"- {exchange.question}")

        output.append("\nIMPORTANT:")
        output.append("Never repeat any question listed above.")
        output.append("Focus only on missing information.")

        return "\n".join(output)

    def latest_question(self):
        return self.exchanges[-1].question if self.exchanges else None

    def latest_answer(self):
        return self.exchanges[-1].answer if self.exchanges else None
    
    def latest_context(self, max_turns: int = 3) -> str:
        """
        Returns only the latest follow-up exchanges.
        Prevents the LLM context from growing forever.
        """

        if not self.exchanges:
            return "No previous follow-up conversation."

        recent = self.exchanges[-max_turns:]

        output = []

        output.append("RECENT FOLLOW-UP HISTORY")
        output.append("=" * 60)

        for i, exchange in enumerate(recent, start=1):

            output.append(f"\nQuestion {i}")
            output.append(exchange.question)

            output.append("\nFounder Response")
            output.append(exchange.answer)

        return "\n".join(output)