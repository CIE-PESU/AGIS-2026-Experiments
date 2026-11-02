import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class WorkerMessage:
    """
    Standard message exchanged between workers.
    Future Kafka messages will follow this contract.
    """

    user_session_id: str

    stage: str

    payload: Any

    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    version: str = "1.0"
