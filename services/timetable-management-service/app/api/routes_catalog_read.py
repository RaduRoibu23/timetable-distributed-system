from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.rbac import require_roles
from app.core.security import verify_token
from app.db import get_db
from app.models import SchoolClass, Subject, TimeSlot, Curriculum, UserProfile, SubjectTeacher


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

class TeacherInfo(BaseModel):
    teacher_id: int
    teacher_username: str | None = None

class CurriculumRead(BaseModel):
    id: int
    class_id: int
    subject_id: int
    hours_per_week: int
    teacher_id: int | None = None  # Legacy, kept for backward compatibility
    teachers: List[TeacherInfo] = []  # List of 1-2 teachers via SubjectTeacher

    model_config = ConfigDict(from_attributes=True)


class CurriculumCreate(BaseModel):
    class_id: int
    subject_id: int
    hours_per_week: int = Field(..., ge=1, le=10)
    teacher_id: int | None = None  # Legacy
    teacher_ids: List[int] = Field(default_factory=list, max_length=2)  # Max 2 teachers


class CurriculumUpdate(BaseModel):
    hours_per_week: int | None = Field(None, ge=1, le=10)
    teacher_id: int | None = None  # Legacy
    teacher_ids: List[int] | None = Field(None, max_length=2)  # Max 2 teachers


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

def _curriculum_to_read_model(curriculum: Curriculum, db: Session) -> CurriculumRead:
    """Convert Curriculum to CurriculumRead with teachers list."""
    teachers = []
    for st in curriculum.subject_teachers:
        teacher_profile = db.query(UserProfile).filter(UserProfile.teacher_id == st.teacher_id).first()
        teachers.append(TeacherInfo(
            teacher_id=st.teacher_id,
            teacher_username=teacher_profile.username if teacher_profile else None,
        ))
    return CurriculumRead(
        id=curriculum.id,
        class_id=curriculum.class_id,
        subject_id=curriculum.subject_id,
        hours_per_week=curriculum.hours_per_week,
        teacher_id=curriculum.teacher_id,
        teachers=teachers,
    )


@router.get("/curricula", response_model=List[CurriculumRead])
def list_curricula(
    class_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    query = db.query(Curriculum)
    if class_id is not None:
        query = query.filter(Curriculum.class_id == class_id)
    curricula = query.all()
    return [_curriculum_to_read_model(c, db) for c in curricula]


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

    # Validate teachers (max 2)
    teacher_ids = curriculum_in.teacher_ids or []
    if curriculum_in.teacher_id is not None and curriculum_in.teacher_id not in teacher_ids:
        teacher_ids.append(curriculum_in.teacher_id)
    if len(teacher_ids) > 2:
        raise HTTPException(status_code=400, detail="Maximum 2 teachers allowed per curriculum")
    
    # Verify all teachers exist
    for tid in teacher_ids:
        teacher_profile = db.query(UserProfile).filter(UserProfile.teacher_id == tid).first()
        if not teacher_profile:
            raise HTTPException(status_code=400, detail=f"Teacher with id {tid} not found")

    curriculum = Curriculum(
        class_id=curriculum_in.class_id,
        subject_id=curriculum_in.subject_id,
        hours_per_week=curriculum_in.hours_per_week,
        teacher_id=curriculum_in.teacher_id,  # Legacy
    )
    db.add(curriculum)
    db.flush()  # Get ID
    
    # Add teachers via SubjectTeacher
    for tid in teacher_ids:
        st = SubjectTeacher(curriculum_id=curriculum.id, teacher_id=tid)
        db.add(st)
    
    try:
        db.commit()
        db.refresh(curriculum)
        return _curriculum_to_read_model(curriculum, db)
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

    if curriculum_in.hours_per_week is not None:
        curriculum.hours_per_week = curriculum_in.hours_per_week
    
    # Update teachers if provided
    if curriculum_in.teacher_ids is not None:
        if len(curriculum_in.teacher_ids) > 2:
            raise HTTPException(status_code=400, detail="Maximum 2 teachers allowed per curriculum")
        
        # Remove existing teachers
        db.query(SubjectTeacher).filter(SubjectTeacher.curriculum_id == curriculum_id).delete()
        
        # Verify and add new teachers
        for tid in curriculum_in.teacher_ids:
            teacher_profile = db.query(UserProfile).filter(UserProfile.teacher_id == tid).first()
            if not teacher_profile:
                raise HTTPException(status_code=400, detail=f"Teacher with id {tid} not found")
            st = SubjectTeacher(curriculum_id=curriculum_id, teacher_id=tid)
            db.add(st)
    
    db.commit()
    db.refresh(curriculum)
    return _curriculum_to_read_model(curriculum, db)


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


# ========= Curriculum Teachers Management =========

@router.post("/curricula/{curriculum_id}/teachers")
def add_teacher_to_curriculum(
    curriculum_id: int,
    teacher_id: int = Query(..., description="Teacher ID to add"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    """Add a teacher to a curriculum. Maximum 2 teachers per curriculum."""
    curriculum = db.query(Curriculum).filter(Curriculum.id == curriculum_id).first()
    if not curriculum:
        raise HTTPException(status_code=404, detail="Curriculum not found")
    
    # Check current teacher count
    current_count = db.query(SubjectTeacher).filter(SubjectTeacher.curriculum_id == curriculum_id).count()
    if current_count >= 2:
        raise HTTPException(status_code=400, detail="Maximum 2 teachers allowed per curriculum")
    
    # Check if teacher already assigned
    existing = db.query(SubjectTeacher).filter(
        SubjectTeacher.curriculum_id == curriculum_id,
        SubjectTeacher.teacher_id == teacher_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Teacher already assigned to this curriculum")
    
    # Verify teacher exists
    teacher_profile = db.query(UserProfile).filter(UserProfile.teacher_id == teacher_id).first()
    if not teacher_profile:
        raise HTTPException(status_code=400, detail="Teacher not found")
    
    st = SubjectTeacher(curriculum_id=curriculum_id, teacher_id=teacher_id)
    db.add(st)
    db.commit()
    return {"detail": "Teacher added to curriculum"}


@router.delete("/curricula/{curriculum_id}/teachers/{teacher_id}")
def remove_teacher_from_curriculum(
    curriculum_id: int,
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    """Remove a teacher from a curriculum."""
    st = db.query(SubjectTeacher).filter(
        SubjectTeacher.curriculum_id == curriculum_id,
        SubjectTeacher.teacher_id == teacher_id,
    ).first()
    if not st:
        raise HTTPException(status_code=404, detail="Teacher not assigned to this curriculum")
    
    db.delete(st)
    db.commit()
    return {"detail": "Teacher removed from curriculum"}


# ========= Subject-Teacher Mapping Endpoints =========

class SubjectTeacherRead(BaseModel):
    curriculum_id: int
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str
    teacher_id: int
    teacher_username: str | None = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/subjects/{subject_id}/teachers", response_model=List[SubjectTeacherRead])
def get_subject_teachers(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    """List all teachers assigned to teach a subject (across all classes)."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    curricula = (
        db.query(Curriculum)
        .filter(
            Curriculum.subject_id == subject_id,
            Curriculum.teacher_id.isnot(None),
        )
        .all()
    )

    result = []
    for curr in curricula:
        class_obj = db.query(SchoolClass).filter(SchoolClass.id == curr.class_id).first()
        teacher_profile = (
            db.query(UserProfile)
            .filter(UserProfile.teacher_id == curr.teacher_id)
            .first()
        )
        result.append(SubjectTeacherRead(
            curriculum_id=curr.id,
            class_id=curr.class_id,
            class_name=class_obj.name if class_obj else "",
            subject_id=curr.subject_id,
            subject_name=subject.name,
            teacher_id=curr.teacher_id,
            teacher_username=teacher_profile.username if teacher_profile else None,
        ))

    return result


class AssignTeacherRequest(BaseModel):
    class_id: int
    teacher_id: int


@router.post("/subjects/{subject_id}/teachers")
def assign_teacher_to_subject(
    subject_id: int,
    request: AssignTeacherRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    """Assign a teacher to teach a subject for a specific class (via Curriculum)."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    curriculum = (
        db.query(Curriculum)
        .filter(
            Curriculum.subject_id == subject_id,
            Curriculum.class_id == request.class_id,
        )
        .first()
    )
    if not curriculum:
        raise HTTPException(status_code=404, detail="Curriculum not found for this subject and class")

    # Verify teacher exists
    teacher_profile = db.query(UserProfile).filter(UserProfile.teacher_id == request.teacher_id).first()
    if not teacher_profile:
        raise HTTPException(status_code=400, detail="Teacher not found")

    curriculum.teacher_id = request.teacher_id
    db.commit()
    db.refresh(curriculum)

    class_obj = db.query(SchoolClass).filter(SchoolClass.id == request.class_id).first()
    return {
        "detail": "Teacher assigned",
        "curriculum_id": curriculum.id,
        "class_id": request.class_id,
        "class_name": class_obj.name if class_obj else "",
        "subject_id": subject_id,
        "subject_name": subject.name,
        "teacher_id": request.teacher_id,
        "teacher_username": teacher_profile.username,
    }


@router.delete("/subjects/{subject_id}/teachers/{teacher_id}")
def remove_teacher_from_subject(
    subject_id: int,
    teacher_id: int,
    class_id: int | None = Query(None, description="Optional class ID to remove assignment for specific class"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    """Remove a teacher assignment from a subject (optionally for a specific class)."""
    
    query = (
        db.query(Curriculum)
        .filter(
            Curriculum.subject_id == subject_id,
            Curriculum.teacher_id == teacher_id,
        )
    )
    if class_id is not None:
        query = query.filter(Curriculum.class_id == class_id)

    curricula = query.all()
    if not curricula:
        raise HTTPException(status_code=404, detail="Teacher assignment not found")

    for curr in curricula:
        curr.teacher_id = None

    db.commit()
    return {"detail": "Teacher assignment removed", "count": len(curricula)}

