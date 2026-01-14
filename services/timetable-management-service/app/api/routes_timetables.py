from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.core.security import verify_token
from app.db import get_db
from app.models import (
    SchoolClass,
    Subject,
    TimeSlot,
    TimetableEntry,
    UserProfile,
)
from app.services.timetable_generator import generate_timetable_for_class


router = APIRouter(prefix="/timetables", tags=["timetables"])


class GenerateRequest(BaseModel):
    class_id: int | None = None
    class_ids: list[int] | None = None


class TimetableEntryRead(BaseModel):
    id: int
    class_id: int
    timeslot_id: int
    subject_id: int
    room_id: int | None = None

    # denormalized fields for frontend
    class_name: str | None = None
    subject_name: str | None = None
    weekday: int | None = None
    index_in_day: int | None = None

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "/generate",
    response_model=List[TimetableEntryRead],
)
def generate_timetables(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["scheduler", "secretariat", "admin", "sysadmin"])),
):
    class_ids: list[int] = []
    if body.class_ids:
        class_ids = list(body.class_ids)
    elif body.class_id is not None:
        class_ids = [body.class_id]
    else:
        raise HTTPException(status_code=400, detail="Provide class_id or class_ids")

    results: list[TimetableEntryRead] = []
    for cid in class_ids:
        entries = generate_timetable_for_class(db, cid)
        results.extend([_to_read_model(db, e) for e in entries])
    return results


@router.get("/classes/{class_id}", response_model=List[TimetableEntryRead])
def get_timetable_for_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    entries = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.class_id == class_id)
        .all()
    )
    return [_to_read_model(db, e) for e in entries]


@router.get("/me", response_model=List[TimetableEntryRead])
def get_my_timetable(
    class_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    username = payload.get("preferred_username")
    roles = (payload.get("realm_access") or {}).get("roles") or []

    # Student: only their own class timetable (from UserProfile mapping)
    if "student" in roles:
        profile = None
        if username:
            profile = (
                db.query(UserProfile)
                .filter(UserProfile.username == username)
                .first()
            )
        if not profile or not profile.class_id:
            raise HTTPException(status_code=400, detail="Student has no class mapping")
        target_class_id = int(profile.class_id)
    else:
        # Others can pass class_id explicitly
        if class_id is None:
            raise HTTPException(status_code=400, detail="Provide class_id")
        target_class_id = int(class_id)

    entries = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.class_id == target_class_id)
        .all()
    )
    return [_to_read_model(db, e) for e in entries]


def _to_read_model(db: Session, entry: TimetableEntry) -> TimetableEntryRead:
    cls = db.query(SchoolClass).filter(SchoolClass.id == entry.class_id).first()
    subj = db.query(Subject).filter(Subject.id == entry.subject_id).first()
    ts = db.query(TimeSlot).filter(TimeSlot.id == entry.timeslot_id).first()

    return TimetableEntryRead(
        id=entry.id,
        class_id=entry.class_id,
        timeslot_id=entry.timeslot_id,
        subject_id=entry.subject_id,
        room_id=entry.room_id,
        class_name=getattr(cls, "name", None),
        subject_name=getattr(subj, "name", None),
        weekday=getattr(ts, "weekday", None),
        index_in_day=getattr(ts, "index_in_day", None),
    )

