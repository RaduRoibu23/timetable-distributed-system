import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # URL-ul realm-ului din Keycloak
    KEYCLOAK_REALM_URL: str = os.getenv(
        "KEYCLOAK_REALM_URL",
        "http://localhost:8181/realms/timetable-realm",
    )

    # ID-ul clientului OIDC din Keycloak
    KEYCLOAK_CLIENT_ID: str = os.getenv(
        "KEYCLOAK_CLIENT_ID",
        "timetable-backend",
    )

    # Issuer-ul așteptat în token
    KEYCLOAK_ISSUER: str = KEYCLOAK_REALM_URL

    # Endpoint-ul de JWKS (cheile publice)
    KEYCLOAK_JWKS_URL: str = f"{KEYCLOAK_REALM_URL}/protocol/openid-connect/certs"


settings = Settings()
