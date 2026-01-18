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

    # Expected token issuer
    KEYCLOAK_ISSUER: str = KEYCLOAK_PUBLIC_REALM_URL

    # JWKS endpoint (public keys)
    KEYCLOAK_JWKS_URL: str = (
        f"{KEYCLOAK_INTERNAL_REALM_URL}/protocol/openid-connect/certs"
    )

    # Keycloak Admin API credentials (for fetching user details)
    KEYCLOAK_ADMIN_URL: str = os.getenv(
        "KEYCLOAK_ADMIN_URL",
        "http://scd_keycloak:8080"  # Internal service name in Docker Swarm
    )
    KEYCLOAK_ADMIN_USER: str = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
    KEYCLOAK_ADMIN_PASSWORD: str = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "timetable-realm")


settings = Settings()
