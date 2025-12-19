from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from jose import jwt
from jose.exceptions import JWTError
from app.core.config import settings
from app.utils.keycloak_client import get_jwks

security = HTTPBearer()


def get_public_key(kid: str):
    """
    Return the correct JWK entry for this kid from the JWKS list.
    """
    jwks = get_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def verify_token(credentials=Depends(security)):
    token = credentials.credentials

    try:
        # Step 1: Get header to extract KID
        headers = jwt.get_unverified_header(token)

        # Step 2: Retrieve correct JWK for this token
        jwk = get_public_key(headers["kid"])
        if not jwk:
            raise HTTPException(status_code=401, detail="Invalid token: unknown KID")

        # Step 3: Decode token using JWK directly
        payload = jwt.decode(
            token,
            jwk,                         # IMPORTANT: use raw JWK
            algorithms=[jwk["alg"]],
            issuer=settings.KEYCLOAK_ISSUER,
            options={"verify_aud": False}
        )

        return payload

    except JWTError as e:
        print("JWT DECODE ERROR:", e)
        raise HTTPException(status_code=401, detail="Invalid token")
