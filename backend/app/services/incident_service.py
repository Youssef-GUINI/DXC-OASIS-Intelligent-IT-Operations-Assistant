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
from app.models.incident_ticket import (
    IncidentSeverity,
    IncidentStatus,
    IncidentTicket,
    IncidentTicketNote,
)


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
            raise ValueError("Incident ticket not found")

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
        raise ValueError("Action not found")
    if action.status != ActionRequestStatus.PENDING:
        raise ValueError(f"Action already handled (current status: {action.status.value})")

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
        # Les tools Storage ne lèvent pas sur une commande refusée par la VM :
        # ils renvoient {"error": "..."} (cf. run_backup, restore_from_backup).
        # Sans ce test, `systemctl start` sur un job qui échoue aussitôt
        # marquerait l'action COMPLETED -- et has_completed_action prendrait
        # une remédiation ratée pour une remédiation faite, jusqu'à clore le
        # ticket sur cette base.
        if isinstance(result, dict) and result.get("error"):
            action.status = ActionRequestStatus.FAILED
        else:
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
        raise ValueError("Action not found")
    if action.status != ActionRequestStatus.PENDING:
        raise ValueError(f"Action already handled (current status: {action.status.value})")

    action.status = ActionRequestStatus.REJECTED
    db.commit()
    db.refresh(action)
    return action


# ======================================================================
# IncidentTicket -- création automatique
# ======================================================================

def _generate_ticket_number(db: Session) -> str:
    """
    Numéro suivant de l'année en cours.

    Dérivé du plus grand numéro existant, et non d'un COUNT : compter suppose
    une suite sans trou. Un seul ticket supprimé, et le compteur repointe sur
    un numéro déjà pris -- l'insertion viole alors l'unicité de
    `ticket_number` et fait tomber tout le passage de surveillance, donc la
    détection elle-même. Le maximum, lui, ne recule jamais.
    """
    year = datetime.utcnow().year
    prefix = f"INC-{year}-"
    highest = db.execute(
        select(func.max(func.substr(IncidentTicket.ticket_number, len(prefix) + 1)))
        .where(IncidentTicket.ticket_number.like(f"{prefix}%"))
    ).scalar_one()

    try:
        next_number = int(highest) + 1
    except (TypeError, ValueError):
        next_number = 1
    return f"{prefix}{next_number:04d}"


def _open_ticket_for(
    db: Session, *, affected_system: str, mcp_data: Optional[dict]
) -> Optional[IncidentTicket]:
    """
    Le ticket ouvert qui porte déjà cette anomalie, s'il existe.

    La correspondance se fait d'abord sur l'identifiant technique relevé dans
    `mcp_data` -- le nom de l'unit systemd, celui du volume -- et seulement
    ensuite sur `affected_system`. Ce dernier est un libellé lisible (la
    Description de l'unit) : le renommer sur la VM suffisait à faire ouvrir un
    second ticket pour le même job, l'ancien restant ouvert à côté.
    """
    open_statuses = [IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS]

    for key in ("job_id", "volume_id"):
        identifier = (mcp_data or {}).get(key)
        if not identifier:
            continue
        match = db.execute(
            select(IncidentTicket).where(
                IncidentTicket.mcp_data[key].astext == str(identifier),
                IncidentTicket.status.in_(open_statuses),
            )
        ).scalars().first()
        if match is not None:
            return match

    return db.execute(
        select(IncidentTicket).where(
            IncidentTicket.affected_system == affected_system,
            IncidentTicket.status.in_(open_statuses),
        )
    ).scalars().first()


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
    existing = _open_ticket_for(db, affected_system=affected_system, mcp_data=mcp_data)

    if existing is not None:
        # La ressource est reconnue par son identifiant technique : son libellé
        # peut avoir changé depuis, et c'est bien le même incident.
        existing.affected_system = affected_system
        # Le titre et la description sont réécrits, et pas seulement le relevé :
        # ils sont produits par la même règle, à partir des mêmes données. Les
        # figer à la première détection laisserait un ticket décrit dans les
        # termes d'une ancienne version des règles -- en français, quand
        # incident_rules est passé à l'anglais -- alors que l'anomalie, elle,
        # est toujours la même et toujours relue à chaque passage.
        existing.title = title
        existing.description = description
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


# ======================================================================
# IncidentTicket -- cycle de vie : prise en charge, notes, clôture
# ======================================================================

def mark_in_progress(db: Session, ticket: IncidentTicket) -> IncidentTicket:
    """
    Passe un ticket ouvert en cours de traitement.

    Appelé quand une investigation démarre : sans cette transition, un ticket
    resterait « open » alors qu'un ingénieur est en train de le diagnostiquer,
    et rien ne distinguerait dans la liste ce qui est pris en charge de ce qui
    attend encore. Un ticket déjà résolu ou clos n'est jamais rouvert ici.
    """
    if ticket.status == IncidentStatus.OPEN:
        ticket.status = IncidentStatus.IN_PROGRESS
        db.commit()
        db.refresh(ticket)
    return ticket


def add_note(
    db: Session, *, ticket_id: uuid.UUID, author_id: int, content: str
) -> IncidentTicketNote:
    """
    Ajoute une note au fil du ticket.

    Les notes forment la piste d'audit du cycle de vie : détection, ouverture
    de l'investigation, action proposée, confirmée ou rejetée, vérification.
    C'est ce qui permet de relire après coup pourquoi un incident a été clos,
    et par qui -- l'horodatage seul des colonnes du ticket ne le dit pas.
    """
    note = IncidentTicketNote(ticket_id=ticket_id, author_id=author_id, content=content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def resolve_ticket(
    db: Session, ticket: IncidentTicket, *, author_id: int, reason: str
) -> IncidentTicket:
    """Clôt un ticket en consignant ce qui l'a justifié."""
    ticket.status = IncidentStatus.RESOLVED
    ticket.resolved_at = datetime.utcnow()
    db.commit()
    add_note(db, ticket_id=ticket.id, author_id=author_id, content=reason)
    db.refresh(ticket)
    return ticket


def pending_actions(db: Session, ticket_id: uuid.UUID) -> list[ActionRequest]:
    """Actions proposées sur ce ticket et encore en attente d'un clic humain."""
    return list(
        db.execute(
            select(ActionRequest)
            .where(
                ActionRequest.incident_ticket_id == ticket_id,
                ActionRequest.status == ActionRequestStatus.PENDING,
            )
            .order_by(ActionRequest.created_at)
        ).scalars().all()
    )


def has_completed_action(db: Session, ticket_id: uuid.UUID) -> bool:
    """
    Vrai si une remédiation a déjà été confirmée et exécutée sur ce ticket.

    Sert de garde à l'auto-résolution : un incident ne se referme pas tout
    seul parce que la VM va mieux, mais parce qu'une action confirmée par un
    humain a produit cet effet. Sans cette condition, un job de sauvegarde qui
    réussit spontanément au cycle suivant clôturerait un ticket que personne
    n'a traité.
    """
    return db.execute(
        select(func.count())
        .select_from(ActionRequest)
        .where(
            ActionRequest.incident_ticket_id == ticket_id,
            ActionRequest.status == ActionRequestStatus.COMPLETED,
        )
    ).scalar_one() > 0
