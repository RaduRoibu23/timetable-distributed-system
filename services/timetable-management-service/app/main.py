from fastapi import FastAPI
from app.api.routes_auth import router as auth_router
from app.api.routes_lessons import router as lessons_router
from app.api.routes_rooms import router as rooms_router
from app.api.routes_catalog_read import router as catalog_router
from app.api.routes_timetables import router as timetables_router
from app.api.routes_notifications import router as notifications_router
from app.api.routes_compat import router as compat_router

from app.db import Base, engine
from app import models  # noqa: F401
from app.init_db import seed_demo_data


app = FastAPI()


@app.on_event("startup")
def on_startup() -> None:
    # Create tables (for dev/demo; production should use migrations)
    Base.metadata.create_all(bind=engine)
    # Seed demo data (idempotent)
    seed_demo_data()


app.include_router(auth_router)
app.include_router(lessons_router)
app.include_router(rooms_router)
app.include_router(catalog_router)
app.include_router(timetables_router)
app.include_router(notifications_router)
app.include_router(compat_router)
