from fastapi import APIRouter, Depends
from app.core.security import verify_token

router = APIRouter()

@router.get("/me")
def get_me(payload: dict = Depends(verify_token)):
    return {
        "username": payload.get("preferred_username"),
        "roles": payload.get("realm_access", {}).get("roles", []),
        "email": payload.get("email")
    }
