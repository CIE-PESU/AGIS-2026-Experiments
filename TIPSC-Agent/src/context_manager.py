from typing import List, Dict


class FollowUpContextManager:
    """
    Responsible for managing the follow-up conversation
    passed back into the TIPSC evaluator.
    """

    def __init__(self):
        self.history: List[Dict[str, str]] = []

    def add_exchange(self, question: str, answer: str):
        self.history.append(
            {
                "question": question.strip(),
                "answer": answer.strip(),
            }
        )

    def build_context(self) -> str:
        if not self.history:
            return "No previous follow-up conversation."

        sections = []

        for i, exchange in enumerate(self.history, start=1):

            sections.append(
f"""Question {i}
{exchange['question']}

Founder Answer
{exchange['answer']}
"""
            )

        return "\n-----------------------------\n".join(sections)

    def conversation_history(self):
        return self.history