from typing import Any

from pydantic import BaseModel


class WorkerOutputRequest(BaseModel):
    correlation_id: str
    flow: str
    output: dict[str, Any]
    duration_seconds: float
    worker_id: str

class WorkerFailureRequest(BaseModel):
    correlation_id: str
    flow: str
    error_code: str
    error_message: str
    retry_count: int = 0
