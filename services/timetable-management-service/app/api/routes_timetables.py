from __future__ import annotations

from typing import List
from collections import Counter

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
    Room,
    TimetableJob,
    ConflictReport,
    Curriculum,
    TeacherAvailability,
    RoomAvailability,
)
from app.services.timetable_generator import generate_timetable_for_class
from app.services import notifications as notifications_service


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


class TimetableEntryUpdate(BaseModel):
    subject_id: int | None = None
    room_id: int | None = None


@router.post(
    "/generate",
    response_model=dict,
)
def generate_timetables(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["scheduler", "secretariat", "admin", "sysadmin"])),
):
    """
    Generate timetables asynchronously via RabbitMQ.
    Returns job IDs for tracking.
    """
    from app.models import TimetableJob
    from app.services import rabbitmq_client
    
    class_ids: list[int] = []
    if body.class_ids:
        class_ids = list(body.class_ids)
    elif body.class_id is not None:
        class_ids = [body.class_id]
    else:
        raise HTTPException(status_code=400, detail="Provide class_id or class_ids")

    from app.services import audit as audit_service
    
    username = current_user.get("preferred_username", "unknown")
    
    job_ids: list[int] = []
    for cid in class_ids:
        # Verify class exists
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == cid).first()
        if not class_obj:
            raise HTTPException(status_code=404, detail=f"Class {cid} not found")
        
        # Create job record
        job = TimetableJob(class_id=cid, status="pending")
        db.add(job)
        db.flush()  # Get ID without committing
        
        # Publish to RabbitMQ
        if rabbitmq_client.publish_timetable_generation_job(cid, job.id):
            db.commit()
            job_ids.append(job.id)
            
            # Log action
            audit_service.log_action(
                db,
                username=username,
                action="timetable_generation_queued",
                resource_type="timetable",
                resource_id=job.id,
                details=f"Queued generation for class {cid}",
            )
        else:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to queue generation job")

    return {"job_ids": job_ids, "message": "Timetable generation jobs queued"}


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


@router.patch("/entries/{entry_id}", response_model=TimetableEntryRead)
def update_timetable_entry(
    entry_id: int,
    entry_in: TimetableEntryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    entry = db.query(TimetableEntry).filter(TimetableEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Timetable entry not found")

    # Optimistic locking: check version
    if entry.version != entry_in.version:
        raise HTTPException(
            status_code=409,
            detail=f"Version mismatch. Expected {entry.version}, got {entry_in.version}. Entry may have been modified by another user."
        )

    if entry_in.subject_id is not None:
        # Verify subject exists
        subject = db.query(Subject).filter(Subject.id == entry_in.subject_id).first()
        if not subject:
            raise HTTPException(status_code=400, detail="Subject not found")
        entry.subject_id = entry_in.subject_id

    if entry_in.room_id is not None:
        # Verify room exists (or allow None to unset)
        if entry_in.room_id == 0:
            entry.room_id = None
        else:
            room = db.query(Room).filter(Room.id == entry_in.room_id).first()
            if not room:
                raise HTTPException(status_code=400, detail="Room not found")
            
            # Advanced validation: Check room capacity vs class size
            student_count = (
                db.query(UserProfile)
                .filter(UserProfile.class_id == entry.class_id)
                .count()
            )
            if student_count > room.capacity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Room capacity ({room.capacity}) is insufficient for class size ({student_count} students)"
                )
            
            # Advanced validation: Check room availability
            from app.models import RoomAvailability, TimeSlot
            timeslot = db.query(TimeSlot).filter(TimeSlot.id == entry.timeslot_id).first()
            if timeslot:
                room_avail = (
                    db.query(RoomAvailability)
                    .filter(
                        RoomAvailability.room_id == entry_in.room_id,
                        RoomAvailability.weekday == timeslot.weekday,
                        RoomAvailability.index_in_day == timeslot.index_in_day,
                    )
                    .first()
                )
                if room_avail and not room_avail.available:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Room is not available at this time slot (weekday {timeslot.weekday}, hour {timeslot.index_in_day})"
                    )
            
            # Advanced validation: Check room overlap (same room, same timeslot, different class)
            overlapping_entry = (
                db.query(TimetableEntry)
                .filter(
                    TimetableEntry.room_id == entry_in.room_id,
                    TimetableEntry.timeslot_id == entry.timeslot_id,
                    TimetableEntry.id != entry_id,  # Exclude current entry
                )
                .first()
            )
            if overlapping_entry:
                other_class = db.query(SchoolClass).filter(SchoolClass.id == overlapping_entry.class_id).first()
                raise HTTPException(
                    status_code=400,
                    detail=f"Room is already occupied by class {other_class.name if other_class else overlapping_entry.class_id} at this time slot"
                )
            
            entry.room_id = entry_in.room_id

    # Advanced validation: Check teacher overlap (if subject_id changed)
    if entry_in.subject_id is not None and entry_in.subject_id != entry.subject_id:
        from app.models import Curriculum, TeacherAvailability, TimeSlot
        # Find teacher for this subject+class combination
        curriculum = (
            db.query(Curriculum)
            .filter(
                Curriculum.subject_id == entry_in.subject_id,
                Curriculum.class_id == entry.class_id,
            )
            .first()
        )
        
        if curriculum and curriculum.teacher_id:
            timeslot = db.query(TimeSlot).filter(TimeSlot.id == entry.timeslot_id).first()
            if timeslot:
                # Check teacher availability
                teacher_avail = (
                    db.query(TeacherAvailability)
                    .filter(
                        TeacherAvailability.teacher_id == curriculum.teacher_id,
                        TeacherAvailability.weekday == timeslot.weekday,
                        TeacherAvailability.index_in_day == timeslot.index_in_day,
                    )
                    .first()
                )
                if teacher_avail and not teacher_avail.available:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Teacher is not available at this time slot (weekday {timeslot.weekday}, hour {timeslot.index_in_day})"
                    )
                
                # Check teacher overlap (same teacher, same timeslot, different class/subject)
                other_entries = (
                    db.query(TimetableEntry)
                    .join(Curriculum, TimetableEntry.subject_id == Curriculum.subject_id)
                    .filter(
                        Curriculum.teacher_id == curriculum.teacher_id,
                        TimetableEntry.timeslot_id == entry.timeslot_id,
                        TimetableEntry.id != entry_id,
                    )
                    .all()
                )
                if other_entries:
                    conflict_details = []
                    for other_entry in other_entries:
                        other_class = db.query(SchoolClass).filter(SchoolClass.id == other_entry.class_id).first()
                        other_subj = db.query(Subject).filter(Subject.id == other_entry.subject_id).first()
                        conflict_details.append(
                            f"class {other_class.name if other_class else other_entry.class_id}, "
                            f"subject {other_subj.name if other_subj else other_entry.subject_id}"
                        )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Teacher already has a lesson at this time slot: {', '.join(conflict_details)}"
                    )

    # Increment version for optimistic locking
    entry.version += 1

    db.commit()
    db.refresh(entry)
    
    # Publish notification event to RabbitMQ (Notifications Service will handle it)
    try:
        from app.services.rabbitmq_client import publish_notification_event
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == entry.class_id).first()
        subject_obj = db.query(Subject).filter(Subject.id == entry.subject_id).first()
        username = current_user.get("preferred_username", "sistem")
        
        publish_notification_event(
            "timetable_entry_modified",
            {
                "class_id": entry.class_id,
                "class_name": class_obj.name if class_obj else f"clasa {entry.class_id}",
                "subject_name": subject_obj.name if subject_obj else f"materia {entry.subject_id}",
                "username": username,
                "entry_id": entry.id,
            }
        )
    except Exception as e:
        print(f"Failed to publish notification event: {e}")
    
    return _to_read_model(db, entry)


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    """Get status of a timetable generation job."""
    from app.models import TimetableJob
    
    job = db.query(TimetableJob).filter(TimetableJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "class_id": job.class_id,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
    }


class ConflictReportRead(BaseModel):
    id: int
    job_id: int
    conflict_type: str
    details: str | None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


@router.get("/jobs/{job_id}/conflicts", response_model=List[ConflictReportRead])
def get_job_conflicts(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    """Get conflict reports for a timetable generation job."""
    from app.models import TimetableJob, ConflictReport
    
    job = db.query(TimetableJob).filter(TimetableJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    conflicts = (
        db.query(ConflictReport)
        .filter(ConflictReport.job_id == job_id)
        .order_by(ConflictReport.created_at)
        .all()
    )
    
    return [
        ConflictReportRead(
            id=c.id,
            job_id=c.job_id,
            conflict_type=c.conflict_type,
            details=c.details,
            created_at=c.created_at.isoformat() if c.created_at else "",
        )
        for c in conflicts
    ]


@router.get("/stats")
def get_timetable_stats(
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    """Get statistics about timetables."""
    from collections import Counter
    from app.models import TimetableJob, ConflictReport, TimeSlot
    
    # Total timetables generated (completed jobs)
    total_generated = (
        db.query(TimetableJob)
        .filter(TimetableJob.status == "completed")
        .count()
    )
    
    # Total conflicts
    total_conflicts = db.query(ConflictReport).count()
    
    # Distribution of subjects by weekday
    entries = db.query(TimetableEntry).all()
    subject_distribution = Counter()
    room_usage = Counter()
    
    for entry in entries:
        timeslot = db.query(TimeSlot).filter(TimeSlot.id == entry.timeslot_id).first()
        if timeslot:
            weekday_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][timeslot.weekday]
            subject = db.query(Subject).filter(Subject.id == entry.subject_id).first()
            if subject:
                subject_distribution[f"{weekday_name} - {subject.name}"] += 1
            
            if entry.room_id:
                room = db.query(Room).filter(Room.id == entry.room_id).first()
                if room:
                    room_usage[room.name] += 1
    
    return {
        "total_timetables_generated": total_generated,
        "total_conflicts": total_conflicts,
        "subject_distribution_by_day": dict(subject_distribution),
        "room_usage": dict(room_usage),
        "total_timetable_entries": len(entries),
    }


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
        version=getattr(entry, "version", 1),
        class_name=getattr(cls, "name", None),
        subject_name=getattr(subj, "name", None),
        weekday=getattr(ts, "weekday", None),
        index_in_day=getattr(ts, "index_in_day", None),
    )

