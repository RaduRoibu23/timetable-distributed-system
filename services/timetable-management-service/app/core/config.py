import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    KEYCLOAK_REALM_URL: str = os.getenv("KEYCLOAK_REALM_URL")  # ex: http://localhost:8080/realms/scd-realm
    KEYCLOAK_CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID")  # ex: timetable-client
    KEYCLOAK_ISSUER: str = f"{KEYCLOAK_REALM_URL}"
    KEYCLOAK_JWKS_URL: str = f"{KEYCLOAK_REALM_URL}/protocol/openid-connect/certs"

settings = Settings()
