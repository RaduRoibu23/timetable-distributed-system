from datetime import time
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from app.core.security import verify_token  # foloseste exact acelasi dependency ca /me
from app.db import get_db
from app.models import Lesson as LessonModel

from fastapi import HTTPException


router = APIRouter(
    prefix="/lessons",
    tags=["lessons"],
)


# ======= Schemas (Pydantic) =======

class LessonBase(BaseModel):
    title: str
    weekday: int = Field(ge=0, le=6)  # 0 = Monday ... 6 = Sunday
    start_time: time
    end_time: time
    location: str | None = None


class LessonCreate(LessonBase):
    pass


class LessonRead(LessonBase):
    id: int
    model_config = ConfigDict(from_attributes=True)



# ======= Endpoints =======

@router.post("/", response_model=LessonRead)
def create_lesson(
    lesson_in: LessonCreate,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
) -> LessonModel:
    lesson = LessonModel(
        title=lesson_in.title,
        weekday=lesson_in.weekday,
        start_time=lesson_in.start_time,
        end_time=lesson_in.end_time,
        location=lesson_in.location,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.get("/", response_model=List[LessonRead])
def list_lessons(
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
) -> List[LessonModel]:
    lessons = db.query(LessonModel).all()
    return lessons

@router.get("/{lesson_id}", response_model=LessonRead)
def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
) -> LessonModel:
    lesson = db.query(LessonModel).filter(LessonModel.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson