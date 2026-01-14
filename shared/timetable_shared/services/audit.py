"""
Audit logging service for tracking important actions.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from timetable_shared.models import AuditLog


def log_action(
    db: Session,
    username: str,
    action: str,
    resource_type: str | None = None,
    resource_id: int | None = None,
    details: str | None = None,
) -> AuditLog:
    """
    Log an action to the audit log.
    
    Args:
        db: Database session
        username: Username who performed the action
        action: Action name (e.g., "timetable_generated", "timetable_updated")
        resource_type: Type of resource affected (e.g., "timetable", "class")
        resource_id: ID of the resource affected
        details: Additional details about the action
        
    Returns:
        The created AuditLog entry
    """
    log_entry = AuditLog(
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
