from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.db import get_db
from app.models import UserProfile, SchoolClass


router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfileRead(BaseModel):
    id: int
    username: str
    class_id: int | None = None
    class_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=List[ProfileRead])
def list_profiles(
    role: Optional[str] = Query(None, description="Filter by role (e.g., 'student')"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "scheduler", "admin", "sysadmin"])),
):
    """
    List all user profiles. Optionally filter by role prefix in username.
    """
    query = db.query(UserProfile)
    
    # Simple filter: if role is "student", filter usernames starting with "student"
    if role:
        query = query.filter(UserProfile.username.like(f"{role}%"))
    
    profiles = query.all()
    
    result = []
    for p in profiles:
        class_name = None
        if p.class_id:
            cls = db.query(SchoolClass).filter(SchoolClass.id == p.class_id).first()
            if cls:
                class_name = cls.name
        
        # Parse first/last name from username (demo format: student01, professor01, etc.)
        # In real app, this would come from Keycloak or a separate table
        parts = p.username.replace("0", " ").replace("1", " ").replace("2", " ").strip().split()
        first_name = parts[0].capitalize() if parts else p.username
        last_name = f"Demo{p.id}"
        
        result.append(ProfileRead(
            id=p.id,
            username=p.username,
            class_id=p.class_id,
            class_name=class_name,
            first_name=first_name,
            last_name=last_name,
        ))
    
    return result
