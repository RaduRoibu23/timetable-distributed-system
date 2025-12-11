# app/init_db.py
from app.db import Base, engine
from app import models


def init_db():
    print("Creating tables in database...")
    Base.metadata.create_all(bind=engine)
    print("Done.")


if __name__ == "__main__":
    init_db()
