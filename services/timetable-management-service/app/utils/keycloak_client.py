import requests
from app.core.config import settings

def get_jwks():
    response = requests.get(settings.KEYCLOAK_JWKS_URL)
    response.raise_for_status()
    return response.json()
