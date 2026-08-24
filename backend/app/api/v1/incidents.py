"""
app/api/v1/incidents.py

Version synchrone : db: Session (pas AsyncSession), routes en `def`
classique (FastAPI les exécute dans un threadpool automatiquement, ce qui
évite de bloquer la boucle d'événements pendant l'accès DB).

`investigate` fait exception et reste `async def` : elle appelle l'agent, qui
enchaîne SSH vers la VM et appels Groq derrière de vrais `await`.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.models.incident_ticket import IncidentSeverity, IncidentStatus, IncidentTicket
from app.models.user import User
from app.schemas.incident import (
    ActionRequestOut,
    IncidentNoteOut,
    IncidentTicketDetail,
    IncidentTicketOut,
    IncidentTicketUpdate,
    InvestigationOut,
)
from app.services import incident_investigation, incident_service

router = APIRouter(prefix="/incidents", tags=["incidents"])

# Investiguer, c'est ouvrir un fil de chat et faire tourner l'agent sur la VM :
# même porte que le chat Storage, et non la simple lecture d'un ticket.
_investigator = require_role("storage_engineer", "administrator")


def _detail(db: Session, ticket: IncidentTicket, user: User) -> IncidentTicketDetail:
    """
    Assemble la fiche complète : le ticket, ses actions, sa piste d'audit.

    Construit à la main plutôt que par `from_attributes` : le nom de l'auteur
    d'une note vit sur la relation `author`, et le fil d'investigation dépend
    de l'utilisateur qui regarde -- deux choses qu'un mapping direct des
    colonnes ne saurait pas produire.
    """
    conversation = incident_investigation.find_conversation(
        db, ticket_id=ticket.id, user_id=user.id
    )
    return IncidentTicketDetail(
        **IncidentTicketOut.model_validate(ticket).model_dump(),
        mcp_data=ticket.mcp_data or {},
        actions=[
            ActionRequestOut.model_validate(action)
            for action in sorted(ticket.action_requests, key=lambda a: a.created_at)
        ],
        notes=[
            IncidentNoteOut(
                id=note.id,
                content=note.content,
                created_at=note.created_at,
                author_name=(note.author.full_name or note.author.email)
                if getattr(note, "author", None)
                else None,
            )
            for note in sorted(ticket.notes, key=lambda n: n.created_at)
        ],
        investigation_conversation_id=conversation.id if conversation else None,
    )


def _require_ticket(db: Session, ticket_id: uuid.UUID) -> IncidentTicket:
    ticket = incident_service.get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Incident ticket not found")
    return ticket


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


@router.get("/{ticket_id}", response_model=IncidentTicketDetail)
def get_incident(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _detail(db, _require_ticket(db, ticket_id), current_user)


@router.post("/{ticket_id}/investigate", response_model=InvestigationOut)
async def investigate_incident(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_investigator),
):
    """
    Ouvre le fil d'investigation du ticket et y fait tourner l'agent.

    Appel long : l'agent lit la VM en SSH puis interroge le modèle. La route
    est volontairement bloquante plutôt que mise en file -- l'ingénieur vient
    de cliquer et attend le diagnostic, un accusé de réception vide ne lui
    apprendrait rien.

    Un fil déjà ouvert est renvoyé sans relancer l'agent.
    """
    ticket = _require_ticket(db, ticket_id)
    try:
        result = await incident_investigation.start(db, ticket=ticket, user=current_user)
    except Exception as error:  # noqa: BLE001 -- VM injoignable, Groq en panne…
        # Rien n'a été écrit : start() fait tourner l'agent avant de créer le
        # fil, précisément pour ne pas laisser une conversation vide derrière
        # un échec. On le dit plutôt que de renvoyer un fil qui n'existe pas.
        raise HTTPException(
            status_code=503,
            detail=f"Investigation is not possible right now: {error}",
        )
    return InvestigationOut(**result, ticket=_detail(db, ticket, current_user))


@router.patch("/{ticket_id}", response_model=IncidentTicketDetail)
def update_incident_status(
    ticket_id: uuid.UUID,
    payload: IncidentTicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Transition de statut décidée par un humain.

    Une clôture manuelle reste possible -- la vérification automatique ne
    couvre pas tous les types d'incident, et un ingénieur peut avoir corrigé
    la cause à la main sur la VM. Elle est en revanche consignée : la note dit
    qui a clos le ticket sans passer par une remédiation vérifiée, ce que le
    seul champ `resolved_at` ne distinguerait pas d'une clôture automatique.
    """
    if payload.status is None:
        raise HTTPException(status_code=400, detail="No status provided")

    ticket = _require_ticket(db, ticket_id)

    if payload.status == IncidentStatus.RESOLVED:
        who = current_user.full_name or current_user.email
        verified = incident_service.has_completed_action(db, ticket.id)
        incident_service.resolve_ticket(
            db,
            ticket,
            author_id=current_user.id,
            reason=(
                f"Closed manually by {who}"
                + (
                    " after a confirmed remediation."
                    if verified
                    else ", with no remediation executed from OASIS."
                )
            ),
        )
    else:
        incident_service.update_ticket_status(db, ticket_id, status=payload.status)
        db.refresh(ticket)

    return _detail(db, ticket, current_user)
