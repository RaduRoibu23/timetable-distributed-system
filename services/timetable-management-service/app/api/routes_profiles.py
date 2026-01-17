from __future__ import annotations

import requests
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.core.config import settings
from app.db import get_db
from app.models import UserProfile, SchoolClass


router = APIRouter(prefix="/profiles", tags=["profiles"])


def get_keycloak_admin_token() -> str | None:
    """Get Keycloak admin token for Admin API access."""
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
            return resp.json().get("access_token")
    except Exception:
        pass
    return None


def get_keycloak_user_info(username: str, admin_token: str | None) -> dict | None:
    """Get user info from Keycloak Admin API."""
    if not admin_token:
        return None
    
    try:
        url = f"{settings.KEYCLOAK_ADMIN_URL}/admin/realms/{settings.KEYCLOAK_REALM}/users"
        headers = {"Authorization": f"Bearer {admin_token}"}
        params = {"username": username, "exact": "true"}
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        if resp.status_code == 200:
            users = resp.json()
            if users and len(users) > 0:
                return users[0]  # Return first match
    except Exception:
        pass
    return None


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
    
    # Get Keycloak admin token once for all users
    admin_token = get_keycloak_admin_token()
    
    result = []
    for p in profiles:
        class_name = None
        if p.class_id:
            cls = db.query(SchoolClass).filter(SchoolClass.id == p.class_id).first()
            if cls:
                class_name = cls.name
        
        # Try to get names from Keycloak
        first_name = None
        last_name = None
        kc_user = get_keycloak_user_info(p.username, admin_token)
        if kc_user:
            first_name = kc_user.get("firstName") or kc_user.get("first_name")
            last_name = kc_user.get("lastName") or kc_user.get("last_name")
        
        # Fallback to username parsing if Keycloak unavailable
        if not first_name or not last_name:
            parts = p.username.replace("0", " ").replace("1", " ").replace("2", " ").strip().split()
            if not first_name:
                first_name = parts[0].capitalize() if parts else p.username
            if not last_name:
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
