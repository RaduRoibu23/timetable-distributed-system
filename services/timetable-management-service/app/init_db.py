from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    SchoolClass,
    Subject,
    TimeSlot,
    Curriculum,
    UserProfile,
)


def _get_or_create(session: Session, model, defaults=None, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    params = dict(kwargs)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    session.add(instance)
    session.flush()  # assign PK
    return instance


def seed_demo_data():
    """
    Seed minimal demo data:
    - Classes: IX-A, IX-B
    - Time slots: Monday–Friday x 1..7 (35)
    - Subjects and curriculum (same for both classes, 35 hours/week)
    - UserProfile for student01 mapped to IX-A
    """

    session: Session = SessionLocal()
    try:
        # Classes
        ix_a = _get_or_create(session, SchoolClass, name="IX-A")
        ix_b = _get_or_create(session, SchoolClass, name="IX-B")

        # Time slots: weekdays 0..4, index_in_day 1..7
        for weekday in range(5):
            for index_in_day in range(1, 8):
                _get_or_create(
                    session,
                    TimeSlot,
                    weekday=weekday,
                    index_in_day=index_in_day,
                )

        # Subjects (simple Romanian-like set)
        subject_defs = [
            ("Limba și literatura română", "RO"),
            ("Matematică", "MAT"),
            ("Informatică", "INFO"),
            ("Fizică", "FIZ"),
            ("Chimie", "CH"),
            ("Biologie", "BIO"),
            ("Istorie", "IST"),
            ("Geografie", "GEO"),
            ("Engleză", "ENG"),
            ("Franceză", "FR"),
            ("Educație fizică", "SPORT"),
            ("Religie", "REL"),
            ("Dirigenție", "DIR"),
        ]

        subjects = {}
        for name, code in subject_defs:
            subj = _get_or_create(
                session,
                Subject,
                name=name,
                short_code=code,
            )
            subjects[code] = subj

        # A simple weekly curriculum of 35 hours per week
        curriculum_pattern = [
            ("RO", 4),
            ("MAT", 4),
            ("INFO", 2),
            ("FIZ", 2),
            ("CH", 2),
            ("BIO", 1),
            ("IST", 2),
            ("GEO", 2),
            ("ENG", 2),
            ("FR", 2),
            ("SPORT", 2),
            ("REL", 1),
            ("DIR", 1),
            # filler to reach 35 hours/week for MVP
            ("RO", 4),
            ("MAT", 4),
        ]

        def ensure_curriculum_for_class(school_class: SchoolClass):
            aggregated = {}
            for code, hours in curriculum_pattern:
                aggregated[code] = aggregated.get(code, 0) + int(hours)

            for code, total_hours in aggregated.items():
                subj = subjects[code]
                row = (
                    session.query(Curriculum)
                    .filter(
                        Curriculum.class_id == school_class.id,
                        Curriculum.subject_id == subj.id,
                    )
                    .first()
                )
                if row:
                    row.hours_per_week = int(total_hours)
                else:
                    session.add(
                        Curriculum(
                            class_id=school_class.id,
                            subject_id=subj.id,
                            hours_per_week=int(total_hours),
                        )
                    )

        ensure_curriculum_for_class(ix_a)
        ensure_curriculum_for_class(ix_b)

        # Map student01 to class IX-A
        _get_or_create(
            session,
            UserProfile,
            username="student01",
            defaults={"class_id": ix_a.id},
        )

        session.commit()

    finally:
        session.close()

# app/init_db.py
from app.db import Base, engine
from app import models


def init_db():
    print("Creating tables in database...")
    Base.metadata.create_all(bind=engine)
    print("Done.")


if __name__ == "__main__":
    init_db()
