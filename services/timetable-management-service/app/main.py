from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes_auth import router as auth_router
from app.api.routes_lessons import router as lessons_router
from app.api.routes_rooms import router as rooms_router
from app.api.routes_catalog_read import router as catalog_router
from app.api.routes_timetables import router as timetables_router
from app.api.routes_notifications import router as notifications_router
from app.api.routes_compat import router as compat_router
from app.api.routes_availability import router as availability_router
from app.api.routes_audit import router as audit_router
from app.api.routes_profiles import router as profiles_router

from app.db import Base, engine
from app import models  # noqa: F401
from app.init_db import seed_demo_data


app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Create tables (for dev/demo; production should use migrations)
    Base.metadata.create_all(bind=engine)
    # Seed demo data (idempotent)
    seed_demo_data()


app.include_router(auth_router)
app.include_router(compat_router)  # Must be before lessons_router to catch /lessons/mine
app.include_router(lessons_router)
app.include_router(rooms_router)
app.include_router(catalog_router)
app.include_router(timetables_router)
app.include_router(notifications_router)
app.include_router(availability_router)
app.include_router(audit_router)
app.include_router(profiles_router)
