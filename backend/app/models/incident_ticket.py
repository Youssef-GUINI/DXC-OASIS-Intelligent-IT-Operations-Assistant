"""
app/models/incident_ticket.py

CORRECTIF : created_by (et IncidentTicketNote.author_id) étaient déclarés
en UUID alors que users.id est un Integer -- PostgreSQL refuse une FK
entre deux types incompatibles. Passage à Integer.

Ticket d'incident créé par l'agent Storage automatiquement en cas
d'anomalie détectée (severity HIGH/CRITICAL), ou sur demande explicite de
l'ingénieur -- mais jamais sans qu'un created_by (utilisateur réel) ne
soit associé.
"""
import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
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
    ticket_number = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(IncidentSeverity), nullable=False)
    status = Column(Enum(IncidentStatus), nullable=False, default=IncidentStatus.OPEN)
    affected_system = Column(String, nullable=False)
    root_cause = Column(Text, nullable=True)
    impact_summary = Column(Text, nullable=True)
    mcp_data = Column(JSONB, nullable=False, default=dict)
    recommendations = Column(JSONB, nullable=False, default=list)
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # CORRIGÉ : Integer (users.id est un Integer, pas un UUID)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    creator = relationship("User")
    notes = relationship("IncidentTicketNote", back_populates="ticket", cascade="all, delete-orphan")
    action_requests = relationship("ActionRequest", back_populates="incident_ticket")


class IncidentTicketNote(Base):
    """Notes ajoutées au fil du traitement de l'incident."""
    __tablename__ = "incident_ticket_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("incident_tickets.id"), nullable=False)

    # CORRIGÉ : Integer
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ticket = relationship("IncidentTicket", back_populates="notes")