"""
app/services/incident_service.py

Logique métier pour :
- estimer la sévérité d'un incident (règles déterministes, pas le LLM)
- créer/mettre à jour des tickets (jamais automatiquement, sur demande explicite)
- créer/confirmer/exécuter des ActionRequest (actions sensibles)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_request import ActionRequest, ActionRequestStatus
from app.models.incident_ticket import (
    IncidentSeverity,
    IncidentStatus,
    IncidentTicket,
    IncidentTicketNote,
)
from app.models.mcp_call import MCPCallStatus
from app.services.mcp_audit import log_mcp_call


# ---------- Sévérité (règles déterministes) ----------

def estimate_severity(health_data: dict) -> IncidentSeverity:
    """
    Calcule la sévérité à partir des alertes déjà produites par
    get_storage_health / analyze_incident. Volontairement déterministe :
    on ne laisse pas le LLM décider seul de la criticité d'un incident.
    """
    alerts = health_data.get("alerts", [])
    severities = {a["severity"] for a in alerts}

    if "critical" in severities:
        return IncidentSeverity.CRITICAL
    if "high" in severities:
        return IncidentSeverity.HIGH
    if "medium" in severities:
        return IncidentSeverity.MEDIUM
    return IncidentSeverity.LOW


# ---------- Tickets ----------

async def _generate_ticket_number(db: AsyncSession) -> str:
    year = datetime.now(timezone.utc).year
    stmt = select(func.count()).select_from(IncidentTicket).where(
        IncidentTicket.ticket_number.like(f"INC-{year}-%")
    )
    count = (await db.execute(stmt)).scalar_one()
    return f"INC-{year}-{count + 1:04d}"


async def create_incident_ticket(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    description: str,
    severity: IncidentSeverity,
    affected_system: str,
    root_cause: str | None = None,
    impact_summary: str | None = None,
    mcp_data: dict | None = None,
    recommendations: list | None = None,
    correlation_id: uuid.UUID | None = None,
) -> IncidentTicket:
    """
    Crée un ticket. À appeler UNIQUEMENT suite à une action explicite de
    l'ingénieur (clic "Créer le ticket"), jamais automatiquement depuis
    analyze_incident même si severity == CRITICAL — l'agent doit se
    contenter de proposer.
    """
    ticket = IncidentTicket(
        ticket_number=await _generate_ticket_number(db),
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
        created_by=user_id,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def add_ticket_note(
    db: AsyncSession, *, ticket_id: uuid.UUID, author_id: uuid.UUID, content: str
) -> IncidentTicketNote:
    note = IncidentTicketNote(ticket_id=ticket_id, author_id=author_id, content=content)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def update_ticket_status(
    db: AsyncSession, *, ticket_id: uuid.UUID, status: IncidentStatus
) -> IncidentTicket:
    ticket = await db.get(IncidentTicket, ticket_id)
    if ticket is None:
        raise ValueError(f"Ticket {ticket_id} introuvable")
    ticket.status = status
    if status == IncidentStatus.RESOLVED:
        ticket.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ticket)
    return ticket


# ---------- Actions sensibles (ActionRequest) ----------

# Tools MCP considérés comme sensibles : ne peuvent être exécutés que via
# une ActionRequest confirmée, jamais directement par l'agent en conversation.
SENSITIVE_TOOLS = {"restore_from_backup", "initiate_failover", "cleanup_expired_snapshots"}


async def create_action_request(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    action_type: str,
    target: str,
    parameters: dict,
    incident_ticket_id: uuid.UUID | None = None,
) -> ActionRequest:
    if action_type not in SENSITIVE_TOOLS:
        raise ValueError(f"{action_type} n'est pas une action sensible enregistrée")

    action = ActionRequest(
        action_type=action_type,
        target=target,
        parameters=parameters,
        status=ActionRequestStatus.PENDING,
        requested_by=user_id,
        incident_ticket_id=incident_ticket_id,
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


async def reject_action_request(
    db: AsyncSession, *, action_id: uuid.UUID, user_id: uuid.UUID
) -> ActionRequest:
    action = await db.get(ActionRequest, action_id)
    if action is None:
        raise ValueError(f"ActionRequest {action_id} introuvable")
    if action.status != ActionRequestStatus.PENDING:
        raise ValueError(f"Action {action_id} n'est plus en attente (status={action.status})")
    action.status = ActionRequestStatus.REJECTED
    action.confirmed_by = user_id
    action.confirmed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(action)
    return action


async def confirm_and_execute_action(
    db: AsyncSession,
    *,
    action_id: uuid.UUID,
    user_id: uuid.UUID,
    mcp_client,  # StorageMCPClient — injecté pour éviter import circulaire
) -> ActionRequest:
    """
    Point unique d'exécution d'une action sensible. C'est ICI, et nulle part
    ailleurs, que confirm=True est ajouté aux arguments envoyés au tool MCP —
    jamais dans agent.py à partir d'un texte utilisateur libre.
    """
    action = await db.get(ActionRequest, action_id)
    if action is None:
        raise ValueError(f"ActionRequest {action_id} introuvable")
    if action.status != ActionRequestStatus.PENDING:
        raise ValueError(f"Action {action_id} n'est plus en attente (status={action.status})")

    action.status = ActionRequestStatus.CONFIRMED
    action.confirmed_by = user_id
    action.confirmed_at = datetime.now(timezone.utc)
    await db.commit()

    call_args = {**action.parameters, "confirm": True}
    try:
        result = await mcp_client.call_tool(
            action.action_type,
            correlation_id=None,
            user_id=user_id,
            **call_args,
        )
        action.status = ActionRequestStatus.COMPLETED
        action.result = result
    except Exception as e:
        action.status = ActionRequestStatus.FAILED
        action.result = {"error": str(e)}
        await log_mcp_call(
            db, user_id=user_id, persona="storage", tool_name=action.action_type,
            arguments=call_args, status=MCPCallStatus.FAILED, error_message=str(e),
            action_request_id=action.id,
        )
    finally:
        action.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(action)

    return action