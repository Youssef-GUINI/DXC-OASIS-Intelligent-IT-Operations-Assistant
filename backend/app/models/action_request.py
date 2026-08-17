"""
app/models/action_request.py

CORRECTIF : requested_by et confirmed_by étaient déclarés en UUID alors
que users.id est un Integer -- même incompatibilité que sur
IncidentTicket.created_by. Passage à Integer.

Représente une action sensible proposée par l'agent (ex: nettoyage de
snapshots, restore, failover) qui ne peut être exécutée qu'après un clic
explicite de l'ingénieur sur un bouton "Confirmer" côté frontend — jamais
sur simple texte "oui" dans le chat.
"""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database.base import Base


class ActionRequestStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class ActionRequest(Base):
    __tablename__ = "action_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    action_type = Column(String, nullable=False, index=True)
    target = Column(String, nullable=False)
    parameters = Column(JSONB, nullable=False, default=dict)
    status = Column(Enum(ActionRequestStatus), nullable=False, default=ActionRequestStatus.PENDING)

    # CORRIGÉS : Integer (users.id est un Integer, pas un UUID)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    incident_ticket_id = Column(UUID(as_uuid=True), ForeignKey("incident_tickets.id"), nullable=True)

    result = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    requester = relationship("User", foreign_keys=[requested_by])
    confirmer = relationship("User", foreign_keys=[confirmed_by])
    incident_ticket = relationship("IncidentTicket", back_populates="action_requests")
    mcp_calls = relationship("MCPCall", back_populates="action_request")