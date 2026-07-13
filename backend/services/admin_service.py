# app/services/admin_service.py
from datetime import datetime, timedelta
from typing import Any, Optional

from repositories.session_repo import session_repo
from repositories.audit_repo import audit_repo

async def get_all_sessions(filters: dict[str, Any], page: int, limit: int):
    """Fetches all sessions without ownership restrictions."""
    return await session_repo.find_all_admin(filters=filters, page=page, limit=limit)

async def get_audit_log(filters: dict[str, Any], page: int, limit: int):
    """Fetches the system-wide audit log."""
    return await audit_repo.find_all_system(filters=filters, page=page, limit=limit)

async def get_metrics() -> dict[str, Any]:
    """Compiles system metrics from Session aggregations and Audit logs."""
    # Get database-level aggregations
    metrics = await session_repo.get_system_metrics()
    
    # Calculate time-bound audit metrics
    now = datetime.utcnow()
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    one_hour_ago = now - timedelta(hours=1)
    
    total_logins = await audit_repo.count_system_events("LOGIN", start_of_today)
    kafka_errors = await audit_repo.count_system_events("KAFKA_PUBLISH_FAILED", one_hour_ago)
    
    # Merge and return
    metrics["total_logins_today"] = total_logins
    metrics["kafka_publish_errors_last_hour"] = kafka_errors
    
    return metrics