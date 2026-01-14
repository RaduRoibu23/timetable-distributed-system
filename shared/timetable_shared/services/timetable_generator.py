from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Iterable

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from timetable_shared.models import Curriculum, TimeSlot, TimetableEntry


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
) -> list[TimetableEntry]:
    """
    Generate a full 5x7 timetable for a class (35 entries).

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

    # Build a pool of subject_ids repeated hours_per_week times
    subject_pool: list[int] = []
    for c in curricula:
        subject_pool.extend([int(c.subject_id)] * int(c.hours_per_week))

    # Shuffle and assign with day constraint (retry approach)
    timeslots_by_day = _group_timeslots_by_day(timeslots)

    def try_build_assignment() -> dict[int, int]:
        random.shuffle(subject_pool)
        pool_iter = iter(subject_pool)
        assignment: dict[int, int] = {}  # timeslot_id -> subject_id
        used_per_day: dict[int, Counter[int]] = {d: Counter() for d in timeslots_by_day}

        # Fill day by day to enforce max per day
        for day, day_slots in timeslots_by_day.items():
            for ts in day_slots:
                # Try to pick a subject from remaining pool that doesn't exceed max/day
                picked = None
                buffer = []
                for _ in range(len(subject_pool)):  # upper bound; we break earlier
                    try:
                        subj = next(pool_iter)
                    except StopIteration:
                        break
                    if used_per_day[day][subj] < max_same_subject_per_day:
                        picked = subj
                        break
                    buffer.append(subj)
                # Put back buffered subjects in random order by extending the remaining pool
                if buffer:
                    # Rebuild pool_iter by chaining buffer + remaining
                    remaining = list(pool_iter)
                    random.shuffle(buffer)
                    pool_iter = iter(buffer + remaining)

                if picked is None:
                    return {}

                assignment[int(ts.id)] = int(picked)
                used_per_day[day][picked] += 1

        return assignment

    assignment: dict[int, int] = {}
    for _ in range(50):  # retries
        assignment = try_build_assignment()
        if assignment:
            break
    if not assignment:
        raise ValueError("Could not generate timetable with the given constraints")

    # Delete existing entries for class and recreate
    db.query(TimetableEntry).filter(TimetableEntry.class_id == class_id).delete()
    db.flush()

    entries = [
        TimetableEntry(
            class_id=class_id,
            timeslot_id=ts_id,
            subject_id=subj_id,
        )
        for ts_id, subj_id in assignment.items()
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
