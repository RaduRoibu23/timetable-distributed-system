# app/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Local: folosim Postgres-ul din docker-compose (user/parola/keycloak).
# In Docker (mai tarziu) vom suprascrie cu env DATABASE_URL.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://keycloak:keycloak@localhost:5432/keycloak",
)

engine = create_engine(
    DATABASE_URL,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
