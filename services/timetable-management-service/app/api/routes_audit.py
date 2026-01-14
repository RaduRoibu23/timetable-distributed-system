from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.rbac import require_roles
from app.core.security import verify_token
from app.db import get_db
from app.models import AuditLog

router = APIRouter(
    prefix="/audit-logs",
    tags=["audit"],
)


class AuditLogRead(BaseModel):
    id: int
    username: str
    action: str
    resource_type: str | None
    resource_id: int | None
    details: str | None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=List[AuditLogRead])
def list_audit_logs(
    username: str | None = Query(None, description="Filter by username"),
    action: str | None = Query(None, description="Filter by action"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "sysadmin"])),
):
    """
    List audit logs with optional filtering and pagination.
    Only accessible by admin and sysadmin roles.
    """
    query = db.query(AuditLog)

    # Apply filters
    filters = []
    if username:
        filters.append(AuditLog.username == username)
    if action:
        filters.append(AuditLog.action == action)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)

    if filters:
        query = query.filter(and_(*filters))

    # Order by most recent first
    query = query.order_by(AuditLog.created_at.desc())

    # Apply pagination
    total = query.count()
    logs = query.offset(offset).limit(limit).all()

    return [
        AuditLogRead(
            id=log.id,
            username=log.username,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]
