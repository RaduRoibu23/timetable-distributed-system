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
    Seed demo data:
    - Classes: IX-A, IX-B, X-A, X-B, XI-A (5 classes)
    - Time slots: Monday–Friday x 1..7 (35)
    - Subjects and curriculum (same for all classes, 35 hours/week)
    - UserProfile for students: student01-10 -> IX-A, student11-20 -> IX-B, etc.
    - UserProfile for professors: professor01-10 with teacher_id
    """

    session: Session = SessionLocal()
    try:
        # Classes (5 classes)
        classes = []
        class_names = ["IX-A", "IX-B", "X-A", "X-B", "XI-A"]
        for name in class_names:
            cls = _get_or_create(session, SchoolClass, name=name)
            classes.append(cls)

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

        # Ensure curriculum for all classes
        for cls in classes:
            ensure_curriculum_for_class(cls)

        # Map students to classes (25 students per class)
        # student01-25 -> IX-A, student26-50 -> IX-B, student51-75 -> X-A, etc.
        students_per_class = 25
        for class_idx, cls in enumerate(classes):
            start_student = class_idx * students_per_class + 1
            end_student = start_student + students_per_class - 1
            for student_num in range(start_student, end_student + 1):
                username = f"student{student_num:02d}"  # student01, student02, etc.
                _get_or_create(
                    session,
                    UserProfile,
                    username=username,
                    defaults={"class_id": cls.id},
                )

        # Map professors (professor01-10) with teacher_id
        # teacher_id is just a sequential number for now
        for prof_num in range(1, 11):
            username = f"professor{prof_num:02d}"  # professor01, professor02, etc.
            _get_or_create(
                session,
                UserProfile,
                username=username,
                defaults={"teacher_id": prof_num},
            )
        
        # Add some rooms for testing
        from app.models import Room
        _get_or_create(session, Room, name="Sala 101", defaults={"capacity": 30})
        _get_or_create(session, Room, name="Sala 102", defaults={"capacity": 25})
        _get_or_create(session, Room, name="Laborator Informatică", defaults={"capacity": 20})
        _get_or_create(session, Room, name="Sala Sport", defaults={"capacity": 50})

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
