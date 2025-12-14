from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Room
from app.api.schemas_room import RoomCreate, RoomOut

router = APIRouter(prefix="/rooms", tags=["Rooms"])

@router.post("/", response_model=RoomOut)
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    db_room = Room(name=room.name, capacity=room.capacity)
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@router.get("/", response_model=list[RoomOut])
def get_rooms(db: Session = Depends(get_db)):
    return db.query(Room).all()

@router.get("/{room_id}", response_model=RoomOut)
def get_room(room_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room

@router.put("/{room_id}", response_model=RoomOut)
def update_room(room_id: int, room: RoomCreate, db: Session = Depends(get_db)):
    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    db_room.name = room.name
    db_room.capacity = room.capacity
    db.commit()
    db.refresh(db_room)
    return db_room

@router.delete("/{room_id}")
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    db.delete(room)
    db.commit()
    return {"detail": "Room deleted"}
