"""
app/services/incident_service.py

Version synchrone -- deps.py confirme que get_db() renvoie une
sqlalchemy.orm.Session classique (pas d'AsyncSession dans ce projet).
Aucun `await` sur les appels DB.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.action_request import ActionRequest, ActionRequestStatus
from app.models.incident_ticket import IncidentSeverity, IncidentStatus, IncidentTicket


# ======================================================================
# ActionRequest -- actions sensibles, exécution toujours confirmée
# ======================================================================

def create_action_request(
    db: Session,
    *,
    user_id: int,
    action_type: str,
    target: str,
    parameters: dict[str, Any],
    incident_ticket_id: Optional[uuid.UUID] = None,
) -> ActionRequest:
    if incident_ticket_id is not None:
        ticket = db.get(IncidentTicket, incident_ticket_id)
        if ticket is None:
            raise ValueError("Ticket d'incident introuvable")

    action = ActionRequest(
        action_type=action_type,
        target=target,
        parameters=parameters,
        status=ActionRequestStatus.PENDING,
        requested_by=user_id,
        incident_ticket_id=incident_ticket_id,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


async def confirm_and_execute_action(
    # NOTE: cette fonction reste "async def" uniquement à cause du
    # `await mcp_client.call_tool(...)` ci-dessous (appel MCP/stdio, pas
    # DB). Tous les accès `db` restent synchrones -- c'est voulu, ne pas
    # ajouter `await` devant `db.get`/`db.commit`/`db.refresh`.
    db: Session,
    *,
    action_id: uuid.UUID,
    user_id: int,
    mcp_client,
) -> ActionRequest:
    action = db.get(ActionRequest, action_id)
    if action is None:
        raise ValueError("Action introuvable")
    if action.status != ActionRequestStatus.PENDING:
        raise ValueError(f"Action déjà traitée (statut actuel : {action.status.value})")

    action.status = ActionRequestStatus.CONFIRMED
    action.confirmed_by = user_id
    action.confirmed_at = datetime.utcnow()
    db.commit()

    try:
        # db + user_id activent l'audit dans mcp_calls : c'est le seul chemin
        # qui exécute un outil destructif, il doit être tracé sans exception.
        result = await mcp_client.call_tool(
            action.action_type,
            db=db,
            user_id=user_id,
            action_request_id=action.id,
            confirm=True,
            **action.parameters,
        )
        action.status = ActionRequestStatus.COMPLETED
        action.result = result
    except Exception as error:  # noqa: BLE001
        action.status = ActionRequestStatus.FAILED
        action.result = {"error": str(error)}

    action.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(action)
    return action


def reject_action_request(
    db: Session,
    *,
    action_id: uuid.UUID,
    user_id: int,
) -> ActionRequest:
    action = db.get(ActionRequest, action_id)
    if action is None:
        raise ValueError("Action introuvable")
    if action.status != ActionRequestStatus.PENDING:
        raise ValueError(f"Action déjà traitée (statut actuel : {action.status.value})")

    action.status = ActionRequestStatus.REJECTED
    db.commit()
    db.refresh(action)
    return action


# ======================================================================
# IncidentTicket -- création automatique
# ======================================================================

def _generate_ticket_number(db: Session) -> str:
    year = datetime.utcnow().year
    prefix = f"INC-{year}-"
    count = db.execute(
        select(func.count())
        .select_from(IncidentTicket)
        .where(IncidentTicket.ticket_number.like(f"{prefix}%"))
    ).scalar_one()
    return f"{prefix}{count + 1:04d}"


def create_ticket_from_diagnosis(
    db: Session,
    *,
    created_by: int,
    title: str,
    description: str,
    severity: IncidentSeverity,
    affected_system: str,
    root_cause: Optional[str] = None,
    impact_summary: Optional[str] = None,
    mcp_data: Optional[dict] = None,
    recommendations: Optional[list[dict]] = None,
    correlation_id: Optional[uuid.UUID] = None,
) -> IncidentTicket:
    existing = db.execute(
        select(IncidentTicket).where(
            IncidentTicket.affected_system == affected_system,
            IncidentTicket.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS]),
        )
    ).scalars().first()

    if existing is not None:
        existing.severity = severity
        existing.impact_summary = impact_summary
        existing.mcp_data = mcp_data or {}
        if recommendations is not None:
            existing.recommendations = recommendations
        db.commit()
        db.refresh(existing)
        return existing

    ticket = IncidentTicket(
        ticket_number=_generate_ticket_number(db),
        title=title,
        description=description,
        severity=severity,
        status=IncidentStatus.OPEN,
        affected_system=affected_system,
        root_cause=root_cause,
        impact_summary=impact_summary,
        mcp_data=mcp_data or {},
        recommendations=recommendations or [],
        correlation_id=correlation_id,
        created_by=created_by,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def list_tickets(
    db: Session,
    *,
    status: Optional[IncidentStatus] = None,
    severity: Optional[IncidentSeverity] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[IncidentTicket]:
    query = select(IncidentTicket)
    if status is not None:
        query = query.where(IncidentTicket.status == status)
    if severity is not None:
        query = query.where(IncidentTicket.severity == severity)
    query = query.order_by(IncidentTicket.created_at.desc()).offset(offset).limit(limit)
    return list(db.execute(query).scalars().all())


def get_ticket(db: Session, ticket_id: uuid.UUID) -> Optional[IncidentTicket]:
    return db.get(IncidentTicket, ticket_id)


def update_ticket_status(
    db: Session, ticket_id: uuid.UUID, *, status: IncidentStatus
) -> Optional[IncidentTicket]:
    ticket = get_ticket(db, ticket_id)
    if ticket is None:
        return None
    ticket.status = status
    if status == IncidentStatus.RESOLVED:
        ticket.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return ticket