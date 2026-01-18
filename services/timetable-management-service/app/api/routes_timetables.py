from __future__ import annotations

import logging
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
    SubjectTeacher,
)
from app.services.timetable_generator import generate_timetable_for_class
from app.services import notifications as notifications_service

# Constants for error messages
WEEKDAY_NAMES = {0: "Luni", 1: "Marți", 2: "Miercuri", 3: "Joi", 4: "Vineri"}
TIME_LABELS = {
    1: "13:00–14:00",
    2: "14:00–15:00",
    3: "15:00–16:00",
    4: "16:00–17:00",
    5: "17:00–18:00",
    6: "18:00–19:00",
    7: "19:00–20:00",
}

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
    version: int = 1  # For optimistic locking

    # denormalized fields for frontend
    class_name: str | None = None
    subject_name: str | None = None
    weekday: int | None = None
    index_in_day: int | None = None
    teacher_name: str | None = None  # Teacher name(s) for this subject/class
    room_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TimetableEntryUpdate(BaseModel):
    subject_id: int | None = None
    room_id: int | None = None
    version: int  # Required for optimistic locking


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
    # Filtreaza entries-urile invalide (fara id) si converteste la read model
    result = []
    for e in entries:
        try:
            if e and hasattr(e, 'id') and e.id is not None:
                result.append(_to_read_model(db, e))
        except (ValueError, AttributeError) as err:
            # Log error dar continua cu restul entries-urilor
            logging.warning(f"Skipping invalid timetable entry: {err}")
    return result


@router.delete("/classes/{class_id}")
def delete_timetable_for_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["scheduler", "secretariat", "admin", "sysadmin"])),
):
    """Delete all timetable entries for a class."""
    # Verify class exists
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Delete all entries for this class
    deleted_count = db.query(TimetableEntry).filter(TimetableEntry.class_id == class_id).delete()
    
    # Log audit entry
    from app.services import audit as audit_service
    username = current_user.get("preferred_username", "unknown")
    audit_service.log_action(
        db,
        username=username,
        action="timetable_deleted",
        resource_type="timetable",
        resource_id=class_id,
        details=f"Deleted {deleted_count} timetable entries for class {school_class.name}",
    )
    
    db.commit()
    return {"detail": f"Deleted {deleted_count} timetable entries for class {school_class.name}"}


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
    # Filtreaza entries-urile invalide (fara id) si converteste la read model
    result = []
    for e in entries:
        try:
            if e and hasattr(e, 'id') and e.id is not None:
                result.append(_to_read_model(db, e))
        except (ValueError, AttributeError) as err:
            import logging
            logging.warning(f"Skipping invalid timetable entry: {err}")
    return result


@router.get("/me/teacher", response_model=List[TimetableEntryRead])
def get_my_teacher_timetable(
    db: Session = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    """Get timetable for current teacher - only shows classes they teach, no empty slots."""
    username = payload.get("preferred_username")
    if not username:
        raise HTTPException(status_code=400, detail="Username not found in token")
    
    # Get teacher profile
    profile = db.query(UserProfile).filter(UserProfile.username == username).first()
    if not profile or not profile.teacher_id:
        raise HTTPException(status_code=400, detail="User is not a teacher")
    
    teacher_id = profile.teacher_id
    
    # Find all curricula where this teacher is assigned via SubjectTeacher
    subject_teachers = db.query(SubjectTeacher).filter(
        SubjectTeacher.teacher_id == teacher_id
    ).all()
    
    curriculum_ids = [st.curriculum_id for st in subject_teachers]
    
    # Also check legacy teacher_id in Curriculum
    legacy_curricula = db.query(Curriculum).filter(
        Curriculum.teacher_id == teacher_id
    ).all()
    legacy_curriculum_ids = [c.id for c in legacy_curricula]
    
    # Combine both
    all_curriculum_ids = list(set(curriculum_ids + legacy_curriculum_ids))
    
    if not all_curriculum_ids:
        return []  # Teacher has no assigned classes
    
    # Get curricula
    curricula = db.query(Curriculum).filter(Curriculum.id.in_(all_curriculum_ids)).all()
    
    # Build list of (class_id, subject_id) pairs
    class_subject_pairs = [(c.class_id, c.subject_id) for c in curricula]
    
    # Get timetable entries for these class/subject combinations
    entries = []
    for class_id, subject_id in class_subject_pairs:
        class_entries = db.query(TimetableEntry).filter(
            TimetableEntry.class_id == class_id,
            TimetableEntry.subject_id == subject_id,
        ).all()
        entries.extend(class_entries)
    
    # Return only actual entries (no empty slots), filtrate pentru entries valide
    result = []
    for e in entries:
        try:
            if e and hasattr(e, 'id') and e.id is not None:
                result.append(_to_read_model(db, e))
        except (ValueError, AttributeError) as err:
            import logging
            logging.warning(f"Skipping invalid timetable entry: {err}")
    return result


@router.patch("/entries/{entry_id}", response_model=TimetableEntryRead)
def update_timetable_entry(
    entry_id: int,
    entry_in: TimetableEntryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["scheduler", "secretariat", "admin", "sysadmin"])),
):
    # Validare entry_id
    if not entry_id or entry_id <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entry_id: {entry_id}. Entry ID must be a positive integer."
        )

    entry = db.query(TimetableEntry).filter(TimetableEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(
            status_code=404, 
            detail=f"Timetable entry with id {entry_id} not found. It may have been deleted or the timetable may have been regenerated. Please refresh the page."
        )

    # Optimistic locking: check version
    if entry.version != entry_in.version:
        raise HTTPException(
            status_code=409,
            detail=f"Version mismatch. Expected {entry.version}, got {entry_in.version}. Entry may have been modified or deleted by another user."
        )

    # Teacher conflict validation - check BEFORE applying any changes
    # This ensures we catch conflicts regardless of what field is being changed
    from app.models import Curriculum, TeacherAvailability, TimeSlot, SubjectTeacher
    timeslot = db.query(TimeSlot).filter(TimeSlot.id == entry.timeslot_id).first()
    if timeslot:
        # Determine which subject to check (new subject if changed, otherwise current)
        subject_id_to_check = entry_in.subject_id if entry_in.subject_id is not None else entry.subject_id
        
        # Find teacher for this subject+class combination
        curriculum = (
            db.query(Curriculum)
            .filter(
                Curriculum.subject_id == subject_id_to_check,
                Curriculum.class_id == entry.class_id,
            )
            .first()
        )
        
        if curriculum:
            # Get all teacher IDs for this curriculum (from SubjectTeacher and legacy teacher_id)
            teacher_ids = []
            
            # Check SubjectTeacher table
            subject_teachers = db.query(SubjectTeacher).filter(
                SubjectTeacher.curriculum_id == curriculum.id
            ).all()
            for st in subject_teachers:
                teacher_ids.append(st.teacher_id)
            
            # Also check legacy teacher_id in Curriculum
            if curriculum.teacher_id and curriculum.teacher_id not in teacher_ids:
                teacher_ids.append(curriculum.teacher_id)
            
            # Check for conflicts for each teacher
            for teacher_id in teacher_ids:
                # Check teacher availability
                teacher_avail = (
                    db.query(TeacherAvailability)
                    .filter(
                        TeacherAvailability.teacher_id == teacher_id,
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
                
                # Check teacher overlap: find other entries with same teacher and same timeslot
                # Method 1: Check via Curriculum.teacher_id (legacy)
                other_entries_via_curriculum = (
                    db.query(TimetableEntry)
                    .join(Curriculum, TimetableEntry.subject_id == Curriculum.subject_id)
                    .filter(
                        Curriculum.teacher_id == teacher_id,
                        TimetableEntry.timeslot_id == entry.timeslot_id,
                        TimetableEntry.id != entry_id,
                    )
                    .all()
                )
                
                # Method 2: Check via SubjectTeacher
                other_entries_via_subject_teacher = (
                    db.query(TimetableEntry)
                    .join(Curriculum, TimetableEntry.subject_id == Curriculum.subject_id)
                    .join(SubjectTeacher, SubjectTeacher.curriculum_id == Curriculum.id)
                    .filter(
                        SubjectTeacher.teacher_id == teacher_id,
                        TimetableEntry.timeslot_id == entry.timeslot_id,
                        TimetableEntry.id != entry_id,
                    )
                    .all()
                )
                
                # Combine and deduplicate
                all_conflicting_entries = list(set(other_entries_via_curriculum + other_entries_via_subject_teacher))
                
                # Filter out the current entry being edited (it's not a conflict if it's the same entry)
                all_conflicting_entries = [e for e in all_conflicting_entries if e.id != entry_id]
                
                if all_conflicting_entries:
                    conflict_details = []
                    for other_entry in all_conflicting_entries:
                        other_class = db.query(SchoolClass).filter(SchoolClass.id == other_entry.class_id).first()
                        other_subj = db.query(Subject).filter(Subject.id == other_entry.subject_id).first()
                        class_name = other_class.name if other_class else f"Clasa {other_entry.class_id}"
                        subject_name = other_subj.name if other_subj else f"Materia {other_entry.subject_id}"
                        conflict_details.append(f"{subject_name} la {class_name}")
                    
                    timeslot_name = f"{WEEKDAY_NAMES.get(timeslot.weekday, f'Ziua {timeslot.weekday}')}, {TIME_LABELS.get(timeslot.index_in_day, f'Ora {timeslot.index_in_day}')}"
                    raise HTTPException(
                        status_code=400,
                        detail=f"Profesorul are deja o oră programată la acest interval ({timeslot_name}): {', '.join(conflict_details)}. Vă rugăm să alegeți alt interval sau alt profesor."
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

            # Constraint: Sport <-> Sala de sport
            # Get subject name (either new or existing)
            current_subject_id = entry_in.subject_id if entry_in.subject_id is not None else entry.subject_id
            subject_obj = db.query(Subject).filter(Subject.id == current_subject_id).first()
            
            # Check if this is the "Sport" room
            is_sport_room = (room.name == "Sala Sport")
            is_sport_subject = (subject_obj and subject_obj.name == "Sport")

            if is_sport_subject and not is_sport_room:
                 raise HTTPException(
                    status_code=400,
                    detail="Materia 'Sport' se poate desfășura doar în 'Sala de sport'."
                )
            
            if not is_sport_subject and is_sport_room:
                 raise HTTPException(
                    status_code=400,
                    detail="Doar materia 'Sport' se poate desfășura în 'Sala de sport'."
                )
            
            entry.room_id = entry_in.room_id

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


# Cache for teacher names to avoid repeated Keycloak calls
_teacher_name_cache = {}
_admin_token_cache = {"token": None, "expires_at": 0}

def _get_teacher_display_name(db: Session, teacher_profile: UserProfile) -> str:
    """Get teacher's display name from Keycloak or fallback to username."""
    # Check cache first
    if teacher_profile.username in _teacher_name_cache:
        return _teacher_name_cache[teacher_profile.username]
    
    from app.core.config import settings
    import requests
    import time
    import re
    
    # Try to get name from Keycloak (with caching)
    admin_token = _admin_token_cache.get("token")
    current_time = time.time()
    
    # Refresh token if expired (cache for 5 minutes)
    if not admin_token or current_time > _admin_token_cache.get("expires_at", 0):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = f"{settings.KEYCLOAK_ADMIN_URL}/realms/master/protocol/openid-connect/token"
                data = {
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": settings.KEYCLOAK_ADMIN_USER,
                    "password": settings.KEYCLOAK_ADMIN_PASSWORD,
                }
                resp = requests.post(url, data=data, timeout=5)
                if resp.status_code == 200:
                    admin_token = resp.json().get("access_token")
                    _admin_token_cache["token"] = admin_token
                    _admin_token_cache["expires_at"] = current_time + 300  # 5 minutes
                    break
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # Exponential backoff: 1s, 2s, 3s
                pass
    
    if admin_token:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = f"{settings.KEYCLOAK_ADMIN_URL}/admin/realms/{settings.KEYCLOAK_REALM}/users"
                headers = {"Authorization": f"Bearer {admin_token}"}
                params = {"username": teacher_profile.username, "exact": "true"}
                resp = requests.get(url, headers=headers, params=params, timeout=5)
                if resp.status_code == 200:
                    users = resp.json()
                    if users and len(users) > 0:
                        kc_user = users[0]
                        first_name = kc_user.get("firstName") or kc_user.get("first_name")
                        last_name = kc_user.get("lastName") or kc_user.get("last_name")
                        if first_name and last_name:
                            # Clean up name: remove username and professorXX patterns
                            display_name = f"{first_name} {last_name}".strip()
                            # Remove username pattern if present (e.g., ", professor13" or "professor13")
                            if teacher_profile.username in display_name:
                                display_name = display_name.replace(teacher_profile.username, "").strip()
                            # Improve regex to catch leading comma/space + professor + digits
                            display_name = re.sub(r'(?:,?\s*)?professor\d+', '', display_name, flags=re.IGNORECASE).strip()
                            display_name = display_name.rstrip(",").strip()
                            _teacher_name_cache[teacher_profile.username] = display_name
                            return display_name
                        elif first_name:
                            display_name = first_name.strip()
                            if teacher_profile.username in display_name:
                                display_name = display_name.replace(teacher_profile.username, "").strip()
                            display_name = re.sub(r'(?:,?\s*)?professor\d+', '', display_name, flags=re.IGNORECASE).strip().rstrip(",").strip()
                            _teacher_name_cache[teacher_profile.username] = display_name
                            return display_name
                        elif last_name:
                            display_name = last_name.strip()
                            if teacher_profile.username in display_name:
                                display_name = display_name.replace(teacher_profile.username, "").strip()
                            display_name = re.sub(r'(?:,?\s*)?professor\d+', '', display_name, flags=re.IGNORECASE).strip().rstrip(",").strip()
                            _teacher_name_cache[teacher_profile.username] = display_name
                            return display_name
                elif resp.status_code == 401:
                    # Token expired, clear cache and don't retry
                    _admin_token_cache["token"] = None
                    _admin_token_cache["expires_at"] = 0
                    break
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # Exponential backoff: 1s, 2s, 3s
                pass
        
        # If all retries failed, clear cache entry to allow retry on next call
        if teacher_profile.username in _teacher_name_cache:
            del _teacher_name_cache[teacher_profile.username]
    
    # Fallback to username
    display_name = teacher_profile.username
    _teacher_name_cache[teacher_profile.username] = display_name
    return display_name


def _to_read_model(db: Session, entry: TimetableEntry) -> TimetableEntryRead:
    # Validare: entry trebuie sa aiba id
    if not entry or not hasattr(entry, 'id') or entry.id is None:
        raise ValueError(f"Invalid TimetableEntry: missing id. Entry: {entry}")

    cls = db.query(SchoolClass).filter(SchoolClass.id == entry.class_id).first()
    subj = db.query(Subject).filter(Subject.id == entry.subject_id).first()
    ts = db.query(TimeSlot).filter(TimeSlot.id == entry.timeslot_id).first()
    room = None
    if entry.room_id is not None and entry.room_id != 0:
        room = db.query(Room).filter(Room.id == entry.room_id).first()
    if room:
        room_name = (room.name or "").strip() or None
    else:
        room_name = f"Sala {entry.room_id}" if (entry.room_id is not None and entry.room_id != 0) else None

    # Get teacher name(s) from Curriculum -> SubjectTeacher or legacy teacher_id
    teacher_name = None
    curriculum = db.query(Curriculum).filter(
        Curriculum.class_id == entry.class_id,
        Curriculum.subject_id == entry.subject_id,
    ).first()
    if curriculum:
        teacher_names = []
        
        # Check SubjectTeacher table (new way)
        subject_teachers = db.query(SubjectTeacher).filter(
            SubjectTeacher.curriculum_id == curriculum.id
        ).all()
        for st in subject_teachers:
            teacher_profile = db.query(UserProfile).filter(
                UserProfile.teacher_id == st.teacher_id
            ).first()
            if teacher_profile:
                display_name = _get_teacher_display_name(db, teacher_profile)
                teacher_names.append(display_name)
        
        # Also check legacy teacher_id in Curriculum
        if curriculum.teacher_id:
            teacher_profile = db.query(UserProfile).filter(
                UserProfile.teacher_id == curriculum.teacher_id
            ).first()
            if teacher_profile:
                display_name = _get_teacher_display_name(db, teacher_profile)
                if display_name not in teacher_names:
                    teacher_names.append(display_name)
        
        if teacher_names:
            teacher_name = ", ".join(teacher_names)  # Join multiple teachers with comma

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
        teacher_name=teacher_name,
        room_name=room_name,
    )

