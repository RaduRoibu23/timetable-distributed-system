from datetime import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.db import get_db
from app.models import Lesson as LessonModel, Room as RoomModel

router = APIRouter(
    prefix="/lessons",
    tags=["lessons"],
)

# ========= Schemas =========

class LessonBase(BaseModel):
    title: str
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    room_id: int | None = None


class LessonCreate(LessonBase):
    pass


class LessonUpdate(LessonBase):
    pass


class LessonRead(BaseModel):
    id: int
    title: str
    weekday: int
    start_time: time
    end_time: time
    location: str | None = None
    model_config = ConfigDict(from_attributes=True)

# ========= Endpoints =========

@router.post("/", response_model=LessonRead)
def create_lesson(
    lesson_in: LessonCreate,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    payload = lesson_in.dict()
    room = None
    if payload.get("room_id"):
        room = db.query(RoomModel).filter(RoomModel.id == payload.get("room_id")).first()
        if not room:
            raise HTTPException(status_code=400, detail="Room does not exist")
        # map room_id -> location (Room.name) because DB stores `location`
        payload.pop("room_id", None)
        payload["location"] = room.name

    lesson = LessonModel(**payload)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.get("/", response_model=List[LessonRead])
def list_lessons(
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    return db.query(LessonModel).all()


@router.get("/{lesson_id}", response_model=LessonRead)
def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    lesson = db.query(LessonModel).filter(LessonModel.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.put("/{lesson_id}", response_model=LessonRead)
def update_lesson(
    lesson_id: int,
    lesson_in: LessonUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    lesson = db.query(LessonModel).filter(LessonModel.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    payload = lesson_in.dict()
    if payload.get("room_id"):
        room = db.query(RoomModel).filter(RoomModel.id == payload.get("room_id")).first()
        if not room:
            raise HTTPException(status_code=400, detail="Room does not exist")
        # map room_id -> location
        payload.pop("room_id", None)
        payload["location"] = room.name

    for field, value in payload.items():
        setattr(lesson, field, value)

    db.commit()
    db.refresh(lesson)
    return lesson


@router.delete("/{lesson_id}", response_model=LessonRead)
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    lesson = db.query(LessonModel).filter(LessonModel.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # capture data to return after deletion
    result = {
        "id": lesson.id,
        "title": lesson.title,
        "weekday": lesson.weekday,
        "start_time": lesson.start_time,
        "end_time": lesson.end_time,
        "location": lesson.location,
    }

    db.delete(lesson)
    db.commit()
    return result
