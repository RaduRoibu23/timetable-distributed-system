from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.db import get_db
from app.models import SchoolClass, Subject, TimeSlot


router = APIRouter(
    prefix="",
    tags=["catalog"],
)


class SchoolClassRead(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class SubjectRead(BaseModel):
    id: int
    name: str
    short_code: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TimeSlotRead(BaseModel):
    id: int
    weekday: int
    index_in_day: int

    model_config = ConfigDict(from_attributes=True)


@router.get("/classes", response_model=List[SchoolClassRead])
def list_classes(
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    return db.query(SchoolClass).order_by(SchoolClass.name).all()


@router.get("/subjects", response_model=List[SubjectRead])
def list_subjects(
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    return db.query(Subject).order_by(Subject.name).all()


@router.get("/timeslots", response_model=List[TimeSlotRead])
def list_timeslots(
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    return (
        db.query(TimeSlot)
        .order_by(TimeSlot.weekday, TimeSlot.index_in_day)
        .all()
    )

