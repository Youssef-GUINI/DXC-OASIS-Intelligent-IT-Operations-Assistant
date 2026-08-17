"""
app/schemas/incident.py

Schémas Pydantic pour l'API incidents/actions. Séparés des modèles SQLAlchemy
pour ne jamais exposer directement les colonnes internes (mcp_data brut, etc.)
sans contrôle.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.incident_ticket import IncidentSeverity, IncidentStatus
from app.models.action_request import ActionRequestStatus


# ---------- Analyse d'incident ----------

class IncidentAnalysisRequest(BaseModel):
    message: str = Field(..., description="Question/incident décrit en langage naturel par l'ingénieur")


class RecommendedAction(BaseModel):
    order: int
    description: str
    # si cette action correspond à un tool MCP sensible exécutable via confirmation
    action_type: str | None = None
    target: str | None = None
    requires_confirmation: bool = False


class IncidentAnalysisResponse(BaseModel):
    correlation_id: uuid.UUID
    diagnostic: str
    root_cause: str
    impact_summary: str
    severity: IncidentSeverity
    recommendations: list[RecommendedAction]
    raw_mcp_data: dict[str, Any]
    ticket_suggested: bool


# ---------- Tickets ----------

class IncidentTicketCreate(BaseModel):
    title: str
    description: str
    severity: IncidentSeverity
    affected_system: str
    root_cause: str | None = None
    impact_summary: str | None = None
    mcp_data: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[RecommendedAction] = Field(default_factory=list)
    correlation_id: uuid.UUID | None = None


class IncidentTicketNoteCreate(BaseModel):
    content: str


class IncidentTicketUpdate(BaseModel):
    status: IncidentStatus | None = None


class IncidentTicketOut(BaseModel):
    id: uuid.UUID
    ticket_number: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    affected_system: str
    root_cause: str | None
    impact_summary: str | None
    recommendations: list[dict]
    created_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True


# ---------- Actions sensibles ----------

class ActionRequestCreate(BaseModel):
    action_type: str
    target: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    incident_ticket_id: uuid.UUID | None = None


class ActionRequestOut(BaseModel):
    id: uuid.UUID
    action_type: str
    target: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: ActionRequestStatus
    incident_ticket_id: uuid.UUID | None = None
    created_at: datetime
    completed_at: datetime | None = None
    result: dict[str, Any] | None

    class Config:
        from_attributes = True


class ActionRequestRejection(BaseModel):
    reason: str | None = None