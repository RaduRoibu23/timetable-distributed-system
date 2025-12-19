import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # URL-ul public al realm-ului din Keycloak (folosit in token-uri)
    KEYCLOAK_PUBLIC_REALM_URL: str = os.getenv(
        "KEYCLOAK_PUBLIC_REALM_URL",
        os.getenv(
            "KEYCLOAK_REALM_URL",
            "http://localhost:8181/realms/timetable-realm",
        ),
    )
    KEYCLOAK_REALM_URL: str = KEYCLOAK_PUBLIC_REALM_URL

    # URL-ul intern folosit de servicii pentru a apela Keycloak din retea
    KEYCLOAK_INTERNAL_REALM_URL: str = os.getenv(
        "KEYCLOAK_INTERNAL_REALM_URL",
        KEYCLOAK_PUBLIC_REALM_URL,
    )

    # ID-ul clientului OIDC din Keycloak
    KEYCLOAK_CLIENT_ID: str = os.getenv(
        "KEYCLOAK_CLIENT_ID",
        "timetable-backend",
    )

    # Issuer-ul așteptat în token
    KEYCLOAK_ISSUER: str = KEYCLOAK_PUBLIC_REALM_URL

    # Endpoint-ul de JWKS (cheile publice)
    KEYCLOAK_JWKS_URL: str = (
        f"{KEYCLOAK_INTERNAL_REALM_URL}/protocol/openid-connect/certs"
    )


settings = Settings()
