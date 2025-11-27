from fastapi import FastAPI

from .routes import timetable_routes

app = FastAPI(title="Timetable Management Service")

app.include_router(timetable_routes.router, prefix="/timetable", tags=["timetable"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
