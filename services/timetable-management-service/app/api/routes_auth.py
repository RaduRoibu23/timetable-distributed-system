from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.db import get_db
from app.models import UserProfile, SchoolClass

router = APIRouter()

@router.get("/me")
def get_me(
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    username = payload.get("preferred_username")
    profile = None
    class_name = None
    if username:
        profile = db.query(UserProfile).filter(UserProfile.username == username).first()
        if profile and profile.class_id:
            cls = db.query(SchoolClass).filter(SchoolClass.id == profile.class_id).first()
            if cls:
                class_name = cls.name

    return {
        "username": username,
        "roles": payload.get("realm_access", {}).get("roles", []),
        "email": payload.get("email"),
        "class_id": getattr(profile, "class_id", None),
        "class_name": class_name,
        "teacher_id": getattr(profile, "teacher_id", None),
    }
