import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.api.v1.auth import router as auth_router
from app.api.v1.linux import router as linux_router
from app.api.v1.storage import router as storage_router
from app.api.v1.actions import router as storage_actions_router
from app.middleware.audit_middleware import AuditMiddleware
from app.api.v1 import cross_domain
from app.api.v1 import admin_routes
from app.api.v1.incidents import router as incidents_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.knowledge import router as knowledge_router
from app.services import metrics_collector


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Démarre le collecteur de métriques disque. C'est lui qui construit
    l'historique affiché par le graphique Storage Performance — sans lui,
    la série reste vide (et l'interface l'annonce).
    """
    collector = asyncio.create_task(metrics_collector.run_forever())
    try:
        yield
    finally:
        collector.cancel()
        try:
            await collector
        except asyncio.CancelledError:
            pass


app = FastAPI(title="OASIS AI Copilot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

app.include_router(cross_domain.router, prefix="/api/v1")
app.include_router(admin_routes.router, prefix="/api/v1")
app.include_router(incidents_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(linux_router, prefix="/api/v1")
app.include_router(storage_router, prefix="/api/v1")
app.include_router(storage_actions_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"status": "OASIS AI Copilot backend running"}

