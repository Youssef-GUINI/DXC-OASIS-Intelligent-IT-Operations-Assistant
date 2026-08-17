"""
app/api/v1/dashboard.py

Routes de lecture du dashboard Storage. Toutes en `def` synchrone : la lecture
de capacité passe par SSH (paramiko, bloquant), FastAPI l'exécute donc dans
son threadpool plutôt que sur la boucle d'événements.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.dashboard import kpi_service
from app.models.user import User
from app.schemas.dashboard import (
    ActivityItem,
    InsightOut,
    OverviewOut,
    PerformanceOut,
)

router = APIRouter(prefix="/storage/dashboard", tags=["dashboard"])

_storage_access = require_role("storage_engineer", "administrator")


@router.get("/overview", response_model=OverviewOut)
def read_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    return kpi_service.get_overview(db)


@router.get("/performance", response_model=PerformanceOut)
def read_performance(
    range: Literal["24h", "7d", "30d"] = "24h",
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    return kpi_service.get_performance(db, range)


@router.get("/activity", response_model=list[ActivityItem])
def read_activity(
    limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    return kpi_service.get_recent_activity(db, limit=limit)


@router.get("/insights", response_model=list[InsightOut])
def read_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    return kpi_service.get_insights(db)
