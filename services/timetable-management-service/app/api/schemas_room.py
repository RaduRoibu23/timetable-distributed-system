from pydantic import BaseModel

class RoomBase(BaseModel):
    name: str
    capacity: int

class RoomCreate(RoomBase):
    pass

class RoomOut(RoomBase):
    id: int

    class Config:
        from_attributes = True
