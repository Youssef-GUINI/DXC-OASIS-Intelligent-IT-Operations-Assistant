import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.api.v1.auth import router as auth_router
from app.api.v1.storage import router as storage_router
from app.api.v1.actions import router as storage_actions_router
from app.middleware.audit_middleware import AuditMiddleware
from app.api.v1 import cross_domain
from app.api.v1 import admin_routes
from app.api.v1.incidents import router as incidents_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.reports import router as reports_router
from app.api.v1.search import router as search_router
from app.dashboard import kpi_service
from app.services import incident_watcher, metrics_collector


async def _prime_storage_health() -> None:
    try:
        await asyncio.to_thread(kpi_service.refresh_health_snapshot)
    except Exception:  # noqa: BLE001 -- la VM peut être injoignable au boot
        logging.getLogger(__name__).warning(
            "Releve de sante Storage indisponible au demarrage", exc_info=True
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Démarre les deux tâches de fond.

    - Le collecteur de métriques disque construit l'historique affiché par le
      graphique Storage Performance — sans lui, la série reste vide (et
      l'interface l'annonce).
    - La surveillance des sauvegardes ouvre un ticket quand un job échoue.
      Sans elle, un échec survenu la nuit n'apparaît dans les incidents que si
      quelqu'un pense à interroger l'agent le lendemain.
    """
    tasks = [
        asyncio.create_task(metrics_collector.run_forever()),
        asyncio.create_task(incident_watcher.run_forever()),
        # Premier relevé de la VM pris à froid, hors du chemin d'une requête :
        # sans lui, le premier affichage du dashboard après un redémarrage
        # attendrait la poignée de main SSH.
        asyncio.create_task(_prime_storage_health()),
    ]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
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
app.include_router(storage_router, prefix="/api/v1")
app.include_router(storage_actions_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"status": "OASIS AI Copilot backend running"}

