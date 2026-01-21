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
        headers = jwt.get_unverified_header(token)

        jwk = get_public_key(headers["kid"])
        if not jwk:
            raise HTTPException(status_code=401, detail="Invalid token: unknown KID")

        payload = jwt.decode(
            token,
            jwk,                        
            algorithms=[jwk["alg"]],
            issuer=settings.KEYCLOAK_ISSUER,
            options={"verify_aud": False}
        )

        return payload

    except JWTError as e:
        print("JWT DECODE ERROR:", e)
        raise HTTPException(status_code=401, detail="Invalid token")
