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
    """Get Keycloak admin token for Admin API access with retry logic."""
    import time
    
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
                return resp.json().get("access_token")
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))  # Exponential backoff: 1s, 2s, 3s
            pass
    return None


def get_keycloak_user_info(username: str, admin_token: str | None) -> dict | None:
    """Get user info from Keycloak Admin API with retry logic."""
    if not admin_token:
        return None
    
    import time
    import logging
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            url = f"{settings.KEYCLOAK_ADMIN_URL}/admin/realms/{settings.KEYCLOAK_REALM}/users"
            headers = {"Authorization": f"Bearer {admin_token}"}
            params = {"username": username, "exact": "true"}
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            if resp.status_code == 200:
                users = resp.json()
                if users and len(users) > 0:
                    user_data = users[0]
                    # Debug: log if names are missing
                    if not user_data.get("firstName") or not user_data.get("lastName"):
                        logging.warning(f"Keycloak user '{username}' missing names: firstName={user_data.get('firstName')}, lastName={user_data.get('lastName')}")
                    return user_data  # Return first match
            elif resp.status_code == 401:
                # Token expired, don't retry
                break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))  # Exponential backoff: 1s, 2s, 3s
            logging.warning(f"Failed to get Keycloak user info for '{username}': {e}")
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
        
        # Fallback only if BOTH names are missing (don't override partial data from Keycloak)
        if not first_name and not last_name:
            # Extract number from username (e.g., "student01" -> "01", "student48" -> "48")
            import re
            match = re.search(r'(\d+)$', p.username)
            if match:
                num_str = match.group(1)
                first_name = f"Demo{num_str}"
                last_name = "Student"
            else:
                # Fallback if no number found
                first_name = p.username
                last_name = "User"
        
        result.append(ProfileRead(
            id=p.id,
            username=p.username,
            class_id=p.class_id,
            class_name=class_name,
            first_name=first_name,
            last_name=last_name,
        ))
    
    return result
