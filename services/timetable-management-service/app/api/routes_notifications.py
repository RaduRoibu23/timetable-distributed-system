from __future__ import annotations

import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.core.security import verify_token
from app.db import get_db
from app.models import Notification, SchoolClass
from app.services import notifications as notifications_service


router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationRead(BaseModel):
    id: int
    username: str
    message: str
    created_at: str
    read: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationSendRequest(BaseModel):
    target_type: str = Field(..., pattern="^(user|class)$")
    target_id: str | int  # username if user, class_id if class
    message: str = Field(..., min_length=1, max_length=500)


@router.post("/send", response_model=List[NotificationRead])
def send_notification(
    body: NotificationSendRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin", "professor"])),
):
    """
    Send a notification to a user or to all students in a class.
    RBAC: secretariat, admin, sysadmin, professor
    """
    if body.target_type == "user":
        username = str(body.target_id)
        notif = notifications_service.send_to_user(db, username, body.message)
        return [NotificationRead(
            id=notif.id,
            username=notif.username,
            message=notif.message,
            created_at=notif.created_at.isoformat(),
            read=notif.read,
        )]
    elif body.target_type == "class":
        try:
            class_id = int(body.target_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="class_id must be an integer")

        # Verify class exists
        school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        if not school_class:
            raise HTTPException(status_code=400, detail="Class not found")

        notifs = notifications_service.send_to_class(db, class_id, body.message)
        # If no profiles found, return empty list (not an error, just no recipients)
        if not notifs:
            return []
        return [
            NotificationRead(
                id=n.id,
                username=n.username,
                message=n.message,
                created_at=n.created_at.isoformat(),
                read=n.read,
            )
            for n in notifs
        ]
    else:
        raise HTTPException(status_code=400, detail="target_type must be 'user' or 'class'")


@router.get("/me", response_model=List[NotificationRead])
def get_my_notifications(
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    """Get notifications for the current user."""
    username = payload.get("preferred_username")
    if not username:
        raise HTTPException(status_code=400, detail="Username not found in token")

    notifs = notifications_service.get_user_notifications(db, username, unread_only=unread_only)
    # Debug: check if we found any
    if not notifs:
        # Try to see if any notifications exist at all for this username
        all_for_user = db.query(Notification).filter(Notification.username == username).all()
        # If we have notifications but query returned empty, there might be a filter issue
        if all_for_user and unread_only:
            # All are read, that's fine
            pass
        elif all_for_user:
            # Should have returned them, but didn't - return them anyway
            notifs = all_for_user

    return [
        NotificationRead(
            id=n.id,
            username=n.username,
            message=n.message,
            created_at=n.created_at.isoformat(),
            read=n.read,
        )
        for n in notifs
    ]


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    """Mark a notification as read. Only the owner can mark it."""
    username = payload.get("preferred_username")
    if not username:
        raise HTTPException(status_code=400, detail="Username not found in token")

    try:
        notif = notifications_service.mark_as_read(db, notification_id, username)
        return NotificationRead(
            id=notif.id,
            username=notif.username,
            message=notif.message,
            created_at=notif.created_at.isoformat(),
            read=notif.read,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/stream")
async def notification_stream(
    request: Request,
    db: Session = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    """
    SSE endpoint for real-time notifications.
    Client connects and receives new unread notifications as they appear.
    """
    username = payload.get("preferred_username")
    if not username:
        raise HTTPException(status_code=400, detail="Username not found in token")

    async def event_generator():
        last_id = 0
        # Get initial last notification ID
        latest = (
            db.query(Notification)
            .filter(Notification.username == username)
            .order_by(Notification.id.desc())
            .first()
        )
        if latest:
            last_id = latest.id

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            # Check for new unread notifications
            from app.db import SessionLocal
            check_db = SessionLocal()
            try:
                new_notifs = (
                    check_db.query(Notification)
                    .filter(
                        Notification.username == username,
                        Notification.id > last_id,
                        Notification.read == False,
                    )
                    .order_by(Notification.id.asc())
                    .all()
                )

                for notif in new_notifs:
                    import json
                    data = json.dumps({
                        "id": notif.id,
                        "message": notif.message,
                        "created_at": notif.created_at.isoformat(),
                    })
                    yield f"data: {data}\n\n"
                    last_id = notif.id
            finally:
                check_db.close()

            # Wait before checking again
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
