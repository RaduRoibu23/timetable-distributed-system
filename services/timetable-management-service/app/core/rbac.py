from __future__ import annotations

from typing import Iterable

from fastapi import Depends, HTTPException

from app.core.security import verify_token


def get_roles_from_payload(payload: dict) -> list[str]:
    realm_access = payload.get("realm_access") or {}
    roles = realm_access.get("roles") or []
    # Normalize to strings only
    return [r for r in roles if isinstance(r, str)]


def require_roles(allowed_roles: Iterable[str]):
    """
    FastAPI dependency: requires the authenticated user to have at least one of
    the `allowed_roles` realm roles.

    Special case: `sysadmin` always allowed (superuser).

    Returns the decoded token payload (same shape as `verify_token`).
    """

    allowed = {r for r in allowed_roles if isinstance(r, str) and r}
    if not allowed:
        raise ValueError("require_roles() called with empty allowed_roles")

    def _dep(payload: dict = Depends(verify_token)) -> dict:
        roles = set(get_roles_from_payload(payload))

        if "sysadmin" in roles:
            return payload

        if roles.intersection(allowed):
            return payload

        raise HTTPException(status_code=403, detail="Forbidden")

    return _dep

