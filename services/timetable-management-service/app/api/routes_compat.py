from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.core.security import verify_token
from app.db import get_db
from app.models import TimetableEntry, UserProfile
from app.api.routes_timetables import (
    TimetableEntryRead,
    _to_read_model,
    GenerateRequest,
)
from app.services.timetable_generator import generate_timetable_for_class
from app.models import SchoolClass, Subject, TimeSlot


router = APIRouter(prefix="", tags=["compat"])


@router.post("/schedule/run", response_model=List[TimetableEntryRead])
def schedule_run_compat(
    body: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["scheduler", "secretariat", "admin", "sysadmin"])),
):
    """
    Compatibility alias for frontend: POST /schedule/run -> POST /timetables/generate
    Accepts same body format as /timetables/generate
    """
    class_ids: list[int] = []
    if body.get("class_ids"):
        class_ids = list(body["class_ids"])
    elif body.get("class_id") is not None:
        class_ids = [int(body["class_id"])]
    else:
        raise HTTPException(status_code=400, detail="Provide class_id or class_ids")

    results: list[TimetableEntryRead] = []
    for cid in class_ids:
        entries = generate_timetable_for_class(db, cid)
        results.extend([_to_read_model(db, e) for e in entries])

        # Send notification to class (same as in routes_timetables)
        from app.services import notifications as notifications_service
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == cid).first()
        if class_obj:
            notifications_service.send_to_class(
                db,
                cid,
                f"Orarul pentru clasa {class_obj.name} a fost generat/actualizat.",
            )

    return results


@router.get("/lessons/mine", response_model=List[TimetableEntryRead])
def lessons_mine_compat(
    class_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    """
    Compatibility alias for frontend: GET /lessons/mine -> GET /timetables/me
    Returns timetable entries for the current user (student sees their class, others need class_id param)
    """
    from app.api.routes_timetables import get_my_timetable
    return get_my_timetable(class_id=class_id, db=db, payload=payload)


@router.get("/users")
def users_compat(
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    """
    Compatibility endpoint for frontend admin actions.
    Returns empty list for now (user management is handled by Keycloak).
    """
    return []
