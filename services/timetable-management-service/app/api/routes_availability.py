from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.rbac import require_roles
from app.core.security import verify_token
from app.db import get_db
from app.models import (
    TeacherAvailability,
    RoomAvailability,
    UserProfile,
    Room,
)

router = APIRouter(
    prefix="",
    tags=["availability"],
)


# =====================
# Schemas (Pydantic)
# =====================

class TeacherAvailabilityRead(BaseModel):
    id: int
    teacher_id: int
    weekday: int
    index_in_day: int
    available: bool

    model_config = ConfigDict(from_attributes=True)


class TeacherAvailabilityCreate(BaseModel):
    weekday: int = Field(..., ge=0, le=4)
    index_in_day: int = Field(..., ge=1, le=7)
    available: bool = True


class TeacherAvailabilityUpdate(BaseModel):
    available: bool


class RoomAvailabilityRead(BaseModel):
    id: int
    room_id: int
    weekday: int
    index_in_day: int
    available: bool

    model_config = ConfigDict(from_attributes=True)


class RoomAvailabilityCreate(BaseModel):
    weekday: int = Field(..., ge=0, le=4)
    index_in_day: int = Field(..., ge=1, le=7)
    available: bool = True


class RoomAvailabilityUpdate(BaseModel):
    available: bool


# =====================
# Teacher Availability Endpoints
# =====================

@router.get("/teachers/{teacher_id}/availability", response_model=List[TeacherAvailabilityRead])
def get_teacher_availability(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    """List availability for a teacher."""
    # Verify teacher exists (has teacher_id in UserProfile)
    profile = db.query(UserProfile).filter(UserProfile.teacher_id == teacher_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Teacher not found")

    availabilities = (
        db.query(TeacherAvailability)
        .filter(TeacherAvailability.teacher_id == teacher_id)
        .order_by(TeacherAvailability.weekday, TeacherAvailability.index_in_day)
        .all()
    )
    return availabilities


@router.post("/teachers/{teacher_id}/availability", response_model=TeacherAvailabilityRead)
def create_teacher_availability(
    teacher_id: int,
    availability_in: TeacherAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["professor", "admin", "sysadmin"])),
):
    """Create availability entry for a teacher."""
    # Verify teacher exists
    profile = db.query(UserProfile).filter(UserProfile.teacher_id == teacher_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Check if professor is modifying their own availability
    roles = (current_user.get("realm_access") or {}).get("roles") or []
    username = current_user.get("preferred_username")
    if "professor" in roles and username:
        # Professor can only modify their own availability
        if profile.username != username:
            raise HTTPException(status_code=403, detail="Can only modify own availability")

    availability = TeacherAvailability(
        teacher_id=teacher_id,
        weekday=availability_in.weekday,
        index_in_day=availability_in.index_in_day,
        available=availability_in.available,
    )
    db.add(availability)
    try:
        db.commit()
        db.refresh(availability)
        return availability
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Availability entry already exists for this teacher, weekday, and time slot"
        )


@router.put("/teachers/{teacher_id}/availability/{availability_id}", response_model=TeacherAvailabilityRead)
def update_teacher_availability(
    teacher_id: int,
    availability_id: int,
    availability_in: TeacherAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["professor", "admin", "sysadmin"])),
):
    """Update availability entry for a teacher."""
    availability = (
        db.query(TeacherAvailability)
        .filter(
            TeacherAvailability.id == availability_id,
            TeacherAvailability.teacher_id == teacher_id,
        )
        .first()
    )
    if not availability:
        raise HTTPException(status_code=404, detail="Availability entry not found")

    # Check if professor is modifying their own availability
    roles = (current_user.get("realm_access") or {}).get("roles") or []
    username = current_user.get("preferred_username")
    if "professor" in roles and username:
        profile = db.query(UserProfile).filter(UserProfile.teacher_id == teacher_id).first()
        if profile and profile.username != username:
            raise HTTPException(status_code=403, detail="Can only modify own availability")

    availability.available = availability_in.available
    db.commit()
    db.refresh(availability)
    return availability


@router.delete("/teachers/{teacher_id}/availability/{availability_id}")
def delete_teacher_availability(
    teacher_id: int,
    availability_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["professor", "admin", "sysadmin"])),
):
    """Delete availability entry for a teacher."""
    availability = (
        db.query(TeacherAvailability)
        .filter(
            TeacherAvailability.id == availability_id,
            TeacherAvailability.teacher_id == teacher_id,
        )
        .first()
    )
    if not availability:
        raise HTTPException(status_code=404, detail="Availability entry not found")

    # Check if professor is modifying their own availability
    roles = (current_user.get("realm_access") or {}).get("roles") or []
    username = current_user.get("preferred_username")
    if "professor" in roles and username:
        profile = db.query(UserProfile).filter(UserProfile.teacher_id == teacher_id).first()
        if profile and profile.username != username:
            raise HTTPException(status_code=403, detail="Can only modify own availability")

    db.delete(availability)
    db.commit()
    return {"detail": "Teacher availability deleted"}


# =====================
# Room Availability Endpoints
# =====================

@router.get("/rooms/{room_id}/availability", response_model=List[RoomAvailabilityRead])
def get_room_availability(
    room_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    """List availability for a room."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    availabilities = (
        db.query(RoomAvailability)
        .filter(RoomAvailability.room_id == room_id)
        .order_by(RoomAvailability.weekday, RoomAvailability.index_in_day)
        .all()
    )
    return availabilities


@router.post("/rooms/{room_id}/availability", response_model=RoomAvailabilityRead)
def create_room_availability(
    room_id: int,
    availability_in: RoomAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    """Create availability entry for a room."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    availability = RoomAvailability(
        room_id=room_id,
        weekday=availability_in.weekday,
        index_in_day=availability_in.index_in_day,
        available=availability_in.available,
    )
    db.add(availability)
    try:
        db.commit()
        db.refresh(availability)
        return availability
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Availability entry already exists for this room, weekday, and time slot"
        )


@router.put("/rooms/{room_id}/availability/{availability_id}", response_model=RoomAvailabilityRead)
def update_room_availability(
    room_id: int,
    availability_id: int,
    availability_in: RoomAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    """Update availability entry for a room."""
    availability = (
        db.query(RoomAvailability)
        .filter(
            RoomAvailability.id == availability_id,
            RoomAvailability.room_id == room_id,
        )
        .first()
    )
    if not availability:
        raise HTTPException(status_code=404, detail="Availability entry not found")

    availability.available = availability_in.available
    db.commit()
    db.refresh(availability)
    return availability


@router.delete("/rooms/{room_id}/availability/{availability_id}")
def delete_room_availability(
    room_id: int,
    availability_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    """Delete availability entry for a room."""
    availability = (
        db.query(RoomAvailability)
        .filter(
            RoomAvailability.id == availability_id,
            RoomAvailability.room_id == room_id,
        )
        .first()
    )
    if not availability:
        raise HTTPException(status_code=404, detail="Availability entry not found")

    db.delete(availability)
    db.commit()
    return {"detail": "Room availability deleted"}
