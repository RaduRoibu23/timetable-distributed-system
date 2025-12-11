from fastapi import FastAPI
from app.api.routes_auth import router as auth_router
from app.api.routes_lessons import router as lessons_router
from app.db import Base, engine
from app import models




app = FastAPI()
models.Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(lessons_router)
