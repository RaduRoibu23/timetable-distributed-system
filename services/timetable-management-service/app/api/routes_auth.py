from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.db import get_db
from app.models import UserProfile, SchoolClass, Curriculum, SubjectTeacher, Subject

router = APIRouter()

@router.get("/me")
def get_me(
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    username = payload.get("preferred_username")
    profile = None
    class_name = None
    subjects_taught = []
    
    if username:
        profile = db.query(UserProfile).filter(UserProfile.username == username).first()
        if profile and profile.class_id:
            cls = db.query(SchoolClass).filter(SchoolClass.id == profile.class_id).first()
            if cls:
                class_name = cls.name
        
        # Get subjects taught by this teacher
        if profile and profile.teacher_id:
            # Check SubjectTeacher table
            subject_teachers = db.query(SubjectTeacher).join(Curriculum).filter(
                SubjectTeacher.teacher_id == profile.teacher_id
            ).all()
            for st in subject_teachers:
                curriculum = db.query(Curriculum).filter(Curriculum.id == st.curriculum_id).first()
                if curriculum:
                    subject = db.query(Subject).filter(Subject.id == curriculum.subject_id).first()
                    if subject and subject.name not in subjects_taught:
                        subjects_taught.append(subject.name)
            
            # Also check legacy teacher_id in Curriculum
            legacy_curricula = db.query(Curriculum).filter(
                Curriculum.teacher_id == profile.teacher_id
            ).all()
            for curr in legacy_curricula:
                subject = db.query(Subject).filter(Subject.id == curr.subject_id).first()
                if subject and subject.name not in subjects_taught:
                    subjects_taught.append(subject.name)

    return {
        "username": username,
        "roles": payload.get("realm_access", {}).get("roles", []),
        "email": payload.get("email"),
        "class_id": getattr(profile, "class_id", None),
        "class_name": class_name,
        "teacher_id": getattr(profile, "teacher_id", None),
        "subjects_taught": subjects_taught,
    }
