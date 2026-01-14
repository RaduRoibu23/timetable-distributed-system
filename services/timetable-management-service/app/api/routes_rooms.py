from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ConfigDict

from app.db import get_db
from app.models import Room as RoomModel
from app.core.security import verify_token
from app.core.rbac import require_roles

router = APIRouter(
    prefix="/rooms",
    tags=["rooms"],
)

# =====================
# Schemas (Pydantic)
# =====================

class RoomBase(BaseModel):
    name: str
    capacity: int


class RoomCreate(RoomBase):
    pass


class RoomRead(RoomBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# =====================
# Endpoints
# =====================

@router.post("/", response_model=RoomRead)
def create_room(
    room_in: RoomCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    room = RoomModel(**room_in.dict())
    db.add(room)

    try:
        db.commit()
        db.refresh(room)
        return room

    except IntegrityError:
        db.rollback()

        # Room exista deja (name UNIQUE) → il returnam
        existing_room = (
            db.query(RoomModel)
            .filter(RoomModel.name == room_in.name)
            .first()
        )

        if not existing_room:
            raise HTTPException(
                status_code=500,
                detail="Room exists but could not be retrieved"
            )

        return existing_room


@router.get("/", response_model=list[RoomRead])
def list_rooms(
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    return db.query(RoomModel).all()


@router.get("/{room_id}", response_model=RoomRead)
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(verify_token),
):
    room = db.query(RoomModel).filter(RoomModel.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.put("/{room_id}", response_model=RoomRead)
def update_room(
    room_id: int,
    room_in: RoomCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    room = db.query(RoomModel).filter(RoomModel.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    room.name = room_in.name
    room.capacity = room_in.capacity
    db.commit()
    db.refresh(room)
    return room


@router.delete("/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["secretariat", "admin", "sysadmin"])),
):
    room = db.query(RoomModel).filter(RoomModel.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    db.delete(room)
    db.commit()
    return {"detail": "Room deleted"}
