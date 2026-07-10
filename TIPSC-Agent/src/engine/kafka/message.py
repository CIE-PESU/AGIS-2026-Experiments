from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


@dataclass
class WorkerMessage:
    """
    Standard message exchanged between workers.
    Future Kafka messages will follow this contract.
    """

    user_session_id: str

    stage: str

    payload: Any

    correlation_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    version: str = "1.0"