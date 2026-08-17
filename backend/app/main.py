from fastapi import FastAPI

from app import models
from app.api.v1.auth import router as auth_router
from app.api.v1.linux import router as linux_router
from app.monitoring.scheduler import start_scheduler

app = FastAPI(title="OASIS AI Copilot", version="0.1.0")

app.include_router(auth_router, prefix="/api/v1")
app.include_router(linux_router, prefix="/api/v1")


@app.on_event("startup")
def on_startup():
    start_scheduler()


@app.get("/")
def root():
    return {"status": "OASIS AI Copilot backend running"}