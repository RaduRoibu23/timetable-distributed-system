# app/models.py
from sqlalchemy import Column, Integer, String, Time, SmallInteger
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
