from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """
    Response schema for a single audit log entry.
    """

    model_config = ConfigDict(from_attributes=True)

    session_id: str | None
    event: str
    actor: str
    actor_role: str
    metadata: dict[str, Any]
    timestamp: datetime