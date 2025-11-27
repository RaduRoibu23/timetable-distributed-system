from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_timetable():
    return {"message": "Timetable endpoint placeholder"}
