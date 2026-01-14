from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.rbac import require_roles
from app.core.security import verify_token
from app.db import get_db
from app.models import SchoolClass, Subject, TimeSlot, Curriculum


router = APIRouter(
    prefix="",
    tags=["catalog"],
)


# ========= Classes =========

class SchoolClassRead(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class SchoolClassCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class SchoolClassUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


# ========= Subjects =========

class SubjectRead(BaseModel):
    id: int
    name: str
    short_code: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    short_code: str | None = Field(None, max_length=20)


class SubjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    short_code: str | None = Field(None, max_length=20)


# ========= Curricula =========

class CurriculumRead(BaseModel):
    id: int
    class_id: int
    subject_id: int
    hours_per_week: int

    model_config = ConfigDict(from_attributes=True)


class CurriculumCreate(BaseModel):
    class_id: int
    subject_id: int
    hours_per_week: int = Field(..., ge=1, le=10)


class CurriculumUpdate(BaseModel):
    hours_per_week: int = Field(..., ge=1, le=10)


# ========= TimeSlots (read-only) =========

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


# ========= Classes CRUD =========

@router.post("/classes", response_model=SchoolClassRead)
def create_class(
    class_in: SchoolClassCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    school_class = SchoolClass(name=class_in.name)
    db.add(school_class)
    try:
        db.commit()
        db.refresh(school_class)
        return school_class
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Class with this name already exists")


@router.put("/classes/{class_id}", response_model=SchoolClassRead)
def update_class(
    class_id: int,
    class_in: SchoolClassUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")

    school_class.name = class_in.name
    try:
        db.commit()
        db.refresh(school_class)
        return school_class
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Class with this name already exists")


@router.delete("/classes/{class_id}")
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")

    db.delete(school_class)
    db.commit()
    return {"detail": "Class deleted"}


# ========= Subjects CRUD =========

@router.post("/subjects", response_model=SubjectRead)
def create_subject(
    subject_in: SubjectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    subject = Subject(
        name=subject_in.name,
        short_code=subject_in.short_code,
    )
    db.add(subject)
    try:
        db.commit()
        db.refresh(subject)
        return subject
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Subject with this name or short_code already exists")


@router.put("/subjects/{subject_id}", response_model=SubjectRead)
def update_subject(
    subject_id: int,
    subject_in: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    if subject_in.name is not None:
        subject.name = subject_in.name
    if subject_in.short_code is not None:
        subject.short_code = subject_in.short_code

    try:
        db.commit()
        db.refresh(subject)
        return subject
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Subject with this name or short_code already exists")


@router.delete("/subjects/{subject_id}")
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    db.delete(subject)
    db.commit()
    return {"detail": "Subject deleted"}


# ========= Curricula CRUD =========

@router.get("/curricula", response_model=List[CurriculumRead])
def list_curricula(
    class_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    query = db.query(Curriculum)
    if class_id is not None:
        query = query.filter(Curriculum.class_id == class_id)
    return query.all()


@router.post("/curricula", response_model=CurriculumRead)
def create_curriculum(
    curriculum_in: CurriculumCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    # Verify class and subject exist
    class_exists = db.query(SchoolClass).filter(SchoolClass.id == curriculum_in.class_id).first()
    if not class_exists:
        raise HTTPException(status_code=400, detail="Class not found")

    subject_exists = db.query(Subject).filter(Subject.id == curriculum_in.subject_id).first()
    if not subject_exists:
        raise HTTPException(status_code=400, detail="Subject not found")

    curriculum = Curriculum(
        class_id=curriculum_in.class_id,
        subject_id=curriculum_in.subject_id,
        hours_per_week=curriculum_in.hours_per_week,
    )
    db.add(curriculum)
    try:
        db.commit()
        db.refresh(curriculum)
        return curriculum
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Curriculum for this class and subject already exists")


@router.put("/curricula/{curriculum_id}", response_model=CurriculumRead)
def update_curriculum(
    curriculum_id: int,
    curriculum_in: CurriculumUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    curriculum = db.query(Curriculum).filter(Curriculum.id == curriculum_id).first()
    if not curriculum:
        raise HTTPException(status_code=404, detail="Curriculum not found")

    curriculum.hours_per_week = curriculum_in.hours_per_week
    db.commit()
    db.refresh(curriculum)
    return curriculum


@router.delete("/curricula/{curriculum_id}")
def delete_curriculum(
    curriculum_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    curriculum = db.query(Curriculum).filter(Curriculum.id == curriculum_id).first()
    if not curriculum:
        raise HTTPException(status_code=404, detail="Curriculum not found")

    db.delete(curriculum)
    db.commit()
    return {"detail": "Curriculum deleted"}

