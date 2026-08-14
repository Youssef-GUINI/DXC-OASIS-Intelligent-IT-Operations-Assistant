"""
app/models/incident_ticket.py

Ticket d'incident créé par l'agent Storage (sur demande explicite de
l'ingénieur, ou automatiquement proposé si sévérité HIGH/CRITICAL —
mais jamais créé sans validation utilisateur, cf. incident_service.py).
"""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database.base import Base


class IncidentSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentTicket(Base):
    __tablename__ = "incident_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identifiant lisible affiché à l'ingénieur, ex: "INC-2026-0042"
    ticket_number = Column(String, unique=True, nullable=False, index=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    severity = Column(Enum(IncidentSeverity), nullable=False)
    status = Column(Enum(IncidentStatus), nullable=False, default=IncidentStatus.OPEN)

    # Système/volume/job concerné, ex: "/data/prod", "job-db01-daily"
    affected_system = Column(String, nullable=False)

    # Cause probable rédigée par Groq à partir des données MCP + RAG
    root_cause = Column(Text, nullable=True)

    # Impact estimé (texte libre rédigé par Groq), ex: "dernier backup valide: 30h"
    impact_summary = Column(Text, nullable=True)

    # Snapshot brut des résultats MCP ayant servi au diagnostic (traçabilité)
    mcp_data = Column(JSONB, nullable=False, default=dict)

    # Liste structurée des actions recommandées (pas exécutées automatiquement)
    recommendations = Column(JSONB, nullable=False, default=list)

    # Relie ce ticket aux appels MCP qui ont servi à l'analyse (mcp_calls.correlation_id)
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    creator = relationship("User")
    notes = relationship("IncidentTicketNote", back_populates="ticket", cascade="all, delete-orphan")
    action_requests = relationship("ActionRequest", back_populates="incident_ticket")


class IncidentTicketNote(Base):
    """Notes ajoutées au fil du traitement de l'incident (point 'mise à jour de tickets')."""

    __tablename__ = "incident_ticket_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("incident_tickets.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ticket = relationship("IncidentTicket", back_populates="notes")