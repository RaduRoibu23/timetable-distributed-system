from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Iterable

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from timetable_shared.models import (
    Curriculum,
    TimeSlot,
    TimetableEntry,
    TeacherAvailability,
    RoomAvailability,
    Room,
    UserProfile,
    ConflictReport,
)


def _group_timeslots_by_day(timeslots: Iterable[TimeSlot]):
    by_day: dict[int, list[TimeSlot]] = defaultdict(list)
    for ts in timeslots:
        by_day[int(ts.weekday)].append(ts)
    for d in by_day:
        by_day[d].sort(key=lambda t: int(t.index_in_day))
    return by_day


def generate_timetable_for_class(
    db: Session,
    class_id: int,
    *,
    max_same_subject_per_day: int = 2,
    seed: int | None = None,
    job_id: int | None = None,
) -> list[TimetableEntry]:
    """
    Generate a full 5x7 timetable for a class (35 entries).
    Enhanced version that considers:
    - Teacher availability
    - Room availability and capacity
    - Preference for earlier hours (avoid late hours 6-7)
    - Conflict reporting

    Assumes TimeSlot table contains 35 slots (weekday 0..4, index_in_day 1..7).
    Curriculum must sum to 35 hours/week for the class.
    """

    if seed is not None:
        random.seed(seed)

    timeslots = (
        db.query(TimeSlot)
        .order_by(TimeSlot.weekday, TimeSlot.index_in_day)
        .all()
    )
    if len(timeslots) != 35:
        raise ValueError(f"Expected 35 timeslots, found {len(timeslots)}")

    curricula = db.query(Curriculum).filter(Curriculum.class_id == class_id).all()
    total_hours = sum(int(c.hours_per_week) for c in curricula)
    if total_hours != 35:
        raise ValueError(f"Curriculum must sum to 35, got {total_hours}")

    # Get class student count for room capacity checks
    student_count = (
        db.query(UserProfile)
        .filter(UserProfile.class_id == class_id)
        .count()
    )

    # Get available rooms (capacity >= student_count)
    available_rooms = (
        db.query(Room)
        .filter(Room.capacity >= student_count)
        .all()
    )

    # Build curriculum with teacher mapping
    curriculum_map: dict[int, Curriculum] = {}  # subject_id -> Curriculum
    for c in curricula:
        curriculum_map[int(c.subject_id)] = c

    # Build a pool of (subject_id, curriculum) tuples
    subject_curriculum_pool: list[tuple[int, Curriculum]] = []
    for c in curricula:
        subject_curriculum_pool.extend([(int(c.subject_id), c)] * int(c.hours_per_week))

    # Shuffle and assign with constraints
    timeslots_by_day = _group_timeslots_by_day(timeslots)
    conflicts: list[dict] = []

    def _is_teacher_available(teacher_id: int | None, weekday: int, index_in_day: int) -> bool:
        """Check if teacher is available at given time slot."""
        if teacher_id is None:
            return True  # No teacher assigned, skip check
        
        teacher_avail = (
            db.query(TeacherAvailability)
            .filter(
                TeacherAvailability.teacher_id == teacher_id,
                TeacherAvailability.weekday == weekday,
                TeacherAvailability.index_in_day == index_in_day,
            )
            .first()
        )
        # If no availability record exists, assume available (default=True)
        if teacher_avail is None:
            return True
        return teacher_avail.available

    def _is_room_available(room_id: int, weekday: int, index_in_day: int) -> bool:
        """Check if room is available at given time slot."""
        room_avail = (
            db.query(RoomAvailability)
            .filter(
                RoomAvailability.room_id == room_id,
                RoomAvailability.weekday == weekday,
                RoomAvailability.index_in_day == index_in_day,
            )
            .first()
        )
        if room_avail is None:
            return True  # No availability record, assume available
        return room_avail.available

    def _get_preferred_timeslots(timeslots_by_day: dict[int, list[TimeSlot]]) -> list[TimeSlot]:
        """Return timeslots sorted by preference (earlier hours preferred)."""
        preferred = []
        for day in sorted(timeslots_by_day.keys()):
            day_slots = timeslots_by_day[day]
            # Prefer hours 1-5, avoid 6-7
            early_slots = [ts for ts in day_slots if 1 <= int(ts.index_in_day) <= 5]
            late_slots = [ts for ts in day_slots if int(ts.index_in_day) >= 6]
            preferred.extend(sorted(early_slots, key=lambda t: int(t.index_in_day)))
            preferred.extend(sorted(late_slots, key=lambda t: int(t.index_in_day)))
        return preferred

    def try_build_assignment() -> dict[int, tuple[int, int | None]]:
        """Returns dict: timeslot_id -> (subject_id, room_id | None)"""
        random.shuffle(subject_curriculum_pool)
        pool_iter = iter(subject_curriculum_pool)
        assignment: dict[int, tuple[int, int | None]] = {}
        used_per_day: dict[int, Counter[int]] = {d: Counter() for d in timeslots_by_day}
        used_rooms: dict[int, set[int]] = defaultdict(set)  # timeslot_id -> set of room_ids
        used_teachers: dict[int, set[int]] = defaultdict(set)  # timeslot_id -> set of teacher_ids

        # Use preferred timeslots (earlier hours first)
        preferred_slots = _get_preferred_timeslots(timeslots_by_day)

        for ts in preferred_slots:
            day = int(ts.weekday)
            picked_subj = None
            picked_curriculum = None
            buffer = []

            # Try to find a subject that fits constraints
            for _ in range(len(subject_curriculum_pool)):
                try:
                    subj_id, curr = next(pool_iter)
                except StopIteration:
                    break

                # Check max per day constraint
                if used_per_day[day][subj_id] >= max_same_subject_per_day:
                    buffer.append((subj_id, curr))
                    continue

                # Check teacher availability
                if curr.teacher_id:
                    if not _is_teacher_available(curr.teacher_id, day, int(ts.index_in_day)):
                        buffer.append((subj_id, curr))
                        continue
                    
                    # Check teacher overlap
                    if curr.teacher_id in used_teachers[int(ts.id)]:
                        buffer.append((subj_id, curr))
                        continue

                picked_subj = subj_id
                picked_curriculum = curr
                break

            # Put back buffered items
            if buffer:
                remaining = list(pool_iter)
                random.shuffle(buffer)
                pool_iter = iter(buffer + remaining)

            if picked_subj is None:
                return {}

            # Try to assign a room
            assigned_room = None
            if available_rooms:
                # Shuffle rooms for variety
                shuffled_rooms = list(available_rooms)
                random.shuffle(shuffled_rooms)
                
                for room in shuffled_rooms:
                    # Check room availability
                    if not _is_room_available(room.id, day, int(ts.index_in_day)):
                        continue
                    
                    # Check room overlap
                    if room.id in used_rooms[int(ts.id)]:
                        continue
                    
                    assigned_room = room.id
                    used_rooms[int(ts.id)].add(room.id)
                    break

            # If no room available, we can still create entry without room (conflict will be reported)
            if assigned_room is None and available_rooms:
                if job_id:
                    conflicts.append({
                        "type": "room_unavailable",
                        "details": f"No available room for class {class_id} at weekday {day}, hour {ts.index_in_day}",
                    })

            assignment[int(ts.id)] = (picked_subj, assigned_room)
            used_per_day[day][picked_subj] += 1
            
            if picked_curriculum and picked_curriculum.teacher_id:
                used_teachers[int(ts.id)].add(picked_curriculum.teacher_id)

        return assignment

    assignment: dict[int, tuple[int, int | None]] = {}
    for attempt in range(100):  # More retries for complex constraints
        assignment = try_build_assignment()
        if assignment and len(assignment) == 35:
            break
    
    if not assignment or len(assignment) < 35:
        if job_id:
            conflicts.append({
                "type": "no_solution",
                "details": f"Could not generate complete timetable for class {class_id} after 100 attempts",
            })
        raise ValueError("Could not generate timetable with the given constraints")

    # Save conflict reports if job_id provided
    if job_id and conflicts:
        for conflict in conflicts:
            conflict_report = ConflictReport(
                job_id=job_id,
                conflict_type=conflict["type"],
                details=conflict["details"],
            )
            db.add(conflict_report)

    # Delete existing entries for class and recreate
    db.query(TimetableEntry).filter(TimetableEntry.class_id == class_id).delete()
    db.flush()

    entries = [
        TimetableEntry(
            class_id=class_id,
            timeslot_id=ts_id,
            subject_id=subj_id,
            room_id=room_id,
            version=1,  # Initialize version for optimistic locking
        )
        for ts_id, (subj_id, room_id) in assignment.items()
    ]

    db.add_all(entries)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    # Refresh IDs
    for e in entries:
        db.refresh(e)
    return entries
