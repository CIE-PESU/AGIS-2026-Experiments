"""Keep repeated fallback notices readable without suppressing provider failures."""

import logging
import threading


class ApproximateTokenCountFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self._seen: set[str] = set()
        self._lock = threading.Lock()

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if not (
            message.startswith("Using an approximate input token count for model ")
            and "because a native token count is unavailable" in message
        ):
            return True
        with self._lock:
            if message in self._seen:
                return False
            self._seen.add(message)
        return True


def configure_agent_log_filters() -> None:
    logger = logging.getLogger("crewai.llms.base_llm")
    if not any(isinstance(item, ApproximateTokenCountFilter) for item in logger.filters):
        logger.addFilter(ApproximateTokenCountFilter())
