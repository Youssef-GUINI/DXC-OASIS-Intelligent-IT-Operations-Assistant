"""
app/api/v1/incidents.py

Version synchrone : db: Session (pas AsyncSession), routes en `def`
classique (FastAPI les exécute dans un threadpool automatiquement, ce qui
évite de bloquer la boucle d'événements pendant l'accès DB).
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.incident_ticket import IncidentSeverity, IncidentStatus
from app.schemas.incident import IncidentTicketOut, IncidentTicketUpdate
from app.services import incident_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentTicketOut])
def list_incidents(
    status: Optional[IncidentStatus] = None,
    severity: Optional[IncidentSeverity] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return incident_service.list_tickets(
        db, status=status, severity=severity, limit=limit, offset=offset,
    )


@router.get("/{ticket_id}", response_model=IncidentTicketOut)
def get_incident(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ticket = incident_service.get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket d'incident introuvable")
    return ticket


@router.patch("/{ticket_id}", response_model=IncidentTicketOut)
def update_incident_status(
    ticket_id: uuid.UUID,
    payload: IncidentTicketUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if payload.status is None:
        raise HTTPException(status_code=400, detail="Aucun statut fourni")

    ticket = incident_service.update_ticket_status(db, ticket_id, status=payload.status)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket d'incident introuvable")
    return ticket