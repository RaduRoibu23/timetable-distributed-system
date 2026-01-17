from __future__ import annotations

import random
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    SchoolClass,
    Subject,
    TimeSlot,
    Curriculum,
    UserProfile,
    SubjectTeacher,
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
    - Classes: 12 clase (IX-A/B/C, X-A/B/C, XI-A/B/C, XII-A/B/C)
    - Time slots: Monday–Friday x 1..7 (35)
    - Subjects and curriculum (same for all classes, 35 hours/week)
    - UserProfile for students: 20-25 per class
    - UserProfile for professors: 15-20 profesori
    - Rooms: 15-20 săli cu capacități variate
    """

    session: Session = SessionLocal()
    try:
        # Classes (12 clase)
        classes = []
        class_names = [
            "IX-A", "IX-B", "IX-C",
            "X-A", "X-B", "X-C",
            "XI-A", "XI-B", "XI-C",
            "XII-A", "XII-B", "XII-C"
        ]
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

            # Get list of unique subject codes (for teacher assignment)
            unique_subjects = list(aggregated.keys())
            
            # Assign one teacher per subject (one-to-one mapping)
            # Each unique subject gets ONE teacher, cycling through available teachers if needed
            subject_to_teacher = {}
            teacher_counter = 1  # Start with teacher_id = 1 (professor01)
            
            # First pass: assign teachers to unique subjects
            # Use 20 teachers (professor01-20) - each subject gets one teacher
            num_teachers = 20
            for code in unique_subjects:
                if code not in subject_to_teacher:
                    subject_to_teacher[code] = teacher_counter
                    teacher_counter = (teacher_counter % num_teachers) + 1  # Cycle through 1-20 (professor01-20)
            
            # Second pass: create/update curriculum entries
            for code, total_hours in aggregated.items():
                subj = subjects[code]
                teacher_id = subject_to_teacher[code]  # Get assigned teacher for this subject
                
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
                    # Update teacher assignment if not set
                    if not row.teacher_id:
                        row.teacher_id = teacher_id
                    session.flush()  # Ensure we have the ID
                    
                    # Check if SubjectTeacher entry exists
                    existing_st = session.query(SubjectTeacher).filter(
                        SubjectTeacher.curriculum_id == row.id,
                        SubjectTeacher.teacher_id == teacher_id,
                    ).first()
                    if not existing_st:
                        st = SubjectTeacher(
                            curriculum_id=row.id,
                            teacher_id=teacher_id,
                        )
                        session.add(st)
                else:
                    new_curriculum = Curriculum(
                        class_id=school_class.id,
                        subject_id=subj.id,
                        hours_per_week=int(total_hours),
                        teacher_id=teacher_id,  # Assign teacher
                    )
                    session.add(new_curriculum)
                    session.flush()  # Get ID for SubjectTeacher
                    
                    # Also add to SubjectTeacher table
                    st = SubjectTeacher(
                        curriculum_id=new_curriculum.id,
                        teacher_id=teacher_id,
                    )
                    session.add(st)

        # Ensure curriculum for all classes
        for cls in classes:
            ensure_curriculum_for_class(cls)

        # Map students to classes (20-25 students per class, random)
        # student01-XX -> IX-A, studentXX+1-YY -> IX-B, etc.
        student_counter = 1
        for class_idx, cls in enumerate(classes):
            students_per_class = random.randint(20, 25)  # Random between 20-25
            for i in range(students_per_class):
                username = f"student{student_counter:03d}"  # student001, student002, etc.
                _get_or_create(
                    session,
                    UserProfile,
                    username=username,
                    defaults={"class_id": cls.id},
                )
                student_counter += 1

        # Map professors (professor01-20) with teacher_id
        # 20 profesori pentru a acoperi 13 materii (fiecare materie primește un profesor)
        num_teachers = 20
        for prof_num in range(1, num_teachers + 1):
            username = f"professor{prof_num:02d}"  # professor01, professor02, etc.
            _get_or_create(
                session,
                UserProfile,
                username=username,
                defaults={"teacher_id": prof_num},
            )
        
        # Add 15-20 rooms with various capacities
        from app.models import Room
        rooms_data = [
            ("Sala 101", 30), ("Sala 102", 25), ("Sala 103", 30),
            ("Sala 201", 35), ("Sala 202", 30), ("Sala 203", 25),
            ("Sala 301", 40), ("Sala 302", 35), ("Sala 303", 30),
            ("Sala 401", 35), ("Sala 402", 30),
            ("Laborator Informatică", 20), ("Laborator Fizică", 25),
            ("Laborator Chimie", 20), ("Laborator Biologie", 25),
            ("Sala Sport", 50), ("Sala Muzică", 30), ("Sala Desen", 25),
            ("Amfiteatru", 60), ("Sala Conferințe", 40)
        ]
        for room_name, capacity in rooms_data:
            _get_or_create(session, Room, name=room_name, defaults={"capacity": capacity})

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
