"""
app/api/v1/incidents.py
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db  # adapter selon deps.py existant
from app.schemas.incident import (
    IncidentAnalysisRequest,
    IncidentAnalysisResponse,
    IncidentTicketCreate,
    IncidentTicketNoteCreate,
    IncidentTicketOut,
    IncidentTicketUpdate,
)
from app.services import incident_service
from app.models.incident_ticket import IncidentTicket
from app.personas.storage.agent import storage_persona  # instance existante

router = APIRouter(prefix="/storage/incidents", tags=["incidents"])


@router.post("/analyze", response_model=IncidentAnalysisResponse)
async def analyze_incident(
    payload: IncidentAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Lance l'analyse multi-outils + RAG. Ne crée AUCUN ticket ni action —
    retourne uniquement un diagnostic et des recommandations. La création
    de ticket est un appel séparé, explicite, sur POST /incidents/.
    """
    analysis = await storage_persona.analyze_incident(
        payload.message, user_id=current_user.id, db=db
    )
    return IncidentAnalysisResponse(
        correlation_id=analysis["correlation_id"],
        diagnostic=analysis["analysis_text"],
        root_cause=analysis["analysis_text"],  # à affiner: parser la section dédiée si le RCA est structuré en JSON par Groq
        impact_summary="",  # idem, à extraire si on structure la sortie Groq en JSON
        severity=analysis["severity"],
        recommendations=[],  # idem
        raw_mcp_data=analysis["raw_mcp_data"],
        ticket_suggested=analysis["ticket_suggested"],
    )


@router.post("/", response_model=IncidentTicketOut)
async def create_ticket(
    payload: IncidentTicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Création explicite d'un ticket, à l'initiative de l'ingénieur uniquement."""
    ticket = await incident_service.create_incident_ticket(
        db,
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        affected_system=payload.affected_system,
        root_cause=payload.root_cause,
        impact_summary=payload.impact_summary,
        mcp_data=payload.mcp_data,
        recommendations=[r.model_dump() for r in payload.recommendations],
        correlation_id=payload.correlation_id,
    )
    return ticket


@router.get("/{ticket_id}", response_model=IncidentTicketOut)
async def get_ticket(ticket_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    ticket = await db.get(IncidentTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return ticket


@router.patch("/{ticket_id}", response_model=IncidentTicketOut)
async def update_ticket(
    ticket_id: uuid.UUID,
    payload: IncidentTicketUpdate,
    db: AsyncSession = Depends(get_db),
):
    if payload.status is None:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    try:
        return await incident_service.update_ticket_status(db, ticket_id=ticket_id, status=payload.status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{ticket_id}/notes")
async def add_note(
    ticket_id: uuid.UUID,
    payload: IncidentTicketNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    note = await incident_service.add_ticket_note(
        db, ticket_id=ticket_id, author_id=current_user.id, content=payload.content
    )
    return {"id": note.id, "created_at": note.created_at}