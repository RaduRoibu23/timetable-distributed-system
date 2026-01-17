# app/models.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Time,
    SmallInteger,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    DateTime,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    weekday = Column(SmallInteger, nullable=False)  # 0 = Monday ... 6 = Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    location = Column(String(100), nullable=True)

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    capacity = Column(Integer, nullable=False)


class SchoolClass(Base):
    __tablename__ = "school_classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)  # ex: IX-A

    # relationships
    curricula = relationship("Curriculum", back_populates="school_class")
    timetable_entries = relationship("TimetableEntry", back_populates="school_class")
    users = relationship("UserProfile", back_populates="school_class")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    short_code = Column(String(20), nullable=True, unique=True)

    curricula = relationship("Curriculum", back_populates="subject")
    timetable_entries = relationship("TimetableEntry", back_populates="subject")


class TimeSlot(Base):
    """
    Represents a position in the weekly grid: weekday + index_in_day (1..7).
    We keep it simple (no concrete clock times for now).
    """

    __tablename__ = "time_slots"

    id = Column(Integer, primary_key=True, index=True)
    weekday = Column(SmallInteger, nullable=False)  # 0 = Monday ... 4 = Friday
    index_in_day = Column(SmallInteger, nullable=False)  # 1..7

    __table_args__ = (
        UniqueConstraint("weekday", "index_in_day", name="uq_timeslot_weekday_index"),
    )

    timetable_entries = relationship("TimetableEntry", back_populates="time_slot")


class Curriculum(Base):
    """
    Weekly curriculum: how many hours per week a class has for a given subject.
    Optionally includes teacher_id for the teacher assigned to teach this subject to this class.
    Supports 1-2 teachers via SubjectTeacher junction table.
    """

    __tablename__ = "curricula"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    hours_per_week = Column(SmallInteger, nullable=False)
    teacher_id = Column(Integer, nullable=True)  # References UserProfile.teacher_id (legacy, kept for backward compatibility)

    __table_args__ = (
        UniqueConstraint("class_id", "subject_id", name="uq_curriculum_class_subject"),
    )

    school_class = relationship("SchoolClass", back_populates="curricula")
    subject = relationship("Subject", back_populates="curricula")
    subject_teachers = relationship("SubjectTeacher", back_populates="curriculum", cascade="all, delete-orphan")


class SubjectTeacher(Base):
    """
    Junction table for many-to-many relationship between Curriculum and Teachers.
    Allows 1-2 teachers per subject/class combination.
    """

    __tablename__ = "subject_teachers"

    id = Column(Integer, primary_key=True, index=True)
    curriculum_id = Column(Integer, ForeignKey("curricula.id"), nullable=False)
    teacher_id = Column(Integer, nullable=False)  # References UserProfile.teacher_id

    __table_args__ = (
        UniqueConstraint("curriculum_id", "teacher_id", name="uq_subject_teacher_curriculum_teacher"),
    )

    curriculum = relationship("Curriculum", back_populates="subject_teachers")


class TimetableEntry(Base):
    """
    One cell in the timetable: (class, timeslot) -> subject (+ optional room).
    Includes version field for optimistic locking.
    """

    __tablename__ = "timetable_entries"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    timeslot_id = Column(Integer, ForeignKey("time_slots.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    version = Column(Integer, nullable=False, default=1)  # For optimistic locking

    __table_args__ = (
        UniqueConstraint(
            "class_id",
            "timeslot_id",
            name="uq_timetable_class_timeslot",
        ),
    )

    school_class = relationship("SchoolClass", back_populates="timetable_entries")
    subject = relationship("Subject", back_populates="timetable_entries")
    time_slot = relationship("TimeSlot", back_populates="timetable_entries")
    room = relationship("Room")


class UserProfile(Base):
    """
    Minimal mapping from username (from Keycloak token) to class / teacher ids.
    """

    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True)

    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=True)
    teacher_id = Column(Integer, nullable=True)  # reserved for future use

    school_class = relationship("SchoolClass", back_populates="users")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    # destinatary: we start simple and target usernames directly
    username = Column(String(100), nullable=False)
    message = Column(String(500), nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    read = Column(Boolean, nullable=False, default=False)


class TimetableJob(Base):
    """
    Tracks asynchronous timetable generation jobs.
    """
    __tablename__ = "timetable_jobs"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    
    status = Column(String(20), nullable=False, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    error_message = Column(String(500), nullable=True)
    
    # Relationship
    school_class = relationship("SchoolClass")


class AuditLog(Base):
    """
    Logs important actions for audit purposes.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)  # e.g., "timetable_generated", "timetable_updated"
    resource_type = Column(String(50), nullable=True)  # e.g., "timetable", "class", "subject"
    resource_id = Column(Integer, nullable=True)
    details = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TeacherAvailability(Base):
    """
    Represents teacher availability for specific time slots.
    """
    __tablename__ = "teacher_availability"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, nullable=False)  # References UserProfile.teacher_id
    weekday = Column(SmallInteger, nullable=False)  # 0 = Monday ... 4 = Friday
    index_in_day = Column(SmallInteger, nullable=False)  # 1..7
    available = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("teacher_id", "weekday", "index_in_day", name="uq_teacher_availability"),
    )


class RoomAvailability(Base):
    """
    Represents room availability for specific time slots.
    """
    __tablename__ = "room_availability"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    weekday = Column(SmallInteger, nullable=False)  # 0 = Monday ... 4 = Friday
    index_in_day = Column(SmallInteger, nullable=False)  # 1..7
    available = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("room_id", "weekday", "index_in_day", name="uq_room_availability"),
    )

    room = relationship("Room")


class ConflictReport(Base):
    """
    Reports conflicts encountered during timetable generation.
    """
    __tablename__ = "conflict_reports"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("timetable_jobs.id"), nullable=False)
    conflict_type = Column(String(50), nullable=False)  # "teacher_unavailable", "room_unavailable", "room_capacity", "no_solution"
    details = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    job = relationship("TimetableJob")
