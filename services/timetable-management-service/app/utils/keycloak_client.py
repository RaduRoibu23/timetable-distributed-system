import requests
from functools import lru_cache
from app.core.config import settings

@lru_cache
def get_jwks():
    response = requests.get(settings.KEYCLOAK_JWKS_URL)
    response.raise_for_status()
    return response.json()
