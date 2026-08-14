"""
app/models/action_request.py

Représente une action sensible proposée par l'agent (ex: nettoyage de
snapshots, restore, failover) qui ne peut être exécutée qu'après un clic
explicite de l'ingénieur sur un bouton "Confirmer" côté frontend — jamais
sur simple texte "oui" dans le chat.
"""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database.base import Base


class ActionRequestStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"     # confirmée par l'utilisateur, en cours d'exécution
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"       # l'utilisateur a explicitement refusé


class ActionRequest(Base):
    __tablename__ = "action_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Nom du tool MCP destiné à être appelé une fois confirmé
    # (doit obligatoirement appartenir à _DESTRUCTIVE_TOOLS ou équivalent "sensible")
    action_type = Column(String, nullable=False, index=True)

    # Cible précise de l'action, ex: volume_id, backup_id, target_site —
    # stockée explicitement en plus de `parameters` pour affichage clair
    # dans le bouton de confirmation ("Confirmer la restauration de vol-03
    # depuis backup-2026-08-10")
    target = Column(String, nullable=False)

    # Arguments complets qui seront envoyés au tool MCP à l'exécution
    # (confirm=True est ajouté par le code au moment de l'exécution, jamais
    # stocké ici tel quel avant confirmation réelle)
    parameters = Column(JSONB, nullable=False, default=dict)

    status = Column(Enum(ActionRequestStatus), nullable=False, default=ActionRequestStatus.PENDING)

    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    confirmed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    incident_ticket_id = Column(UUID(as_uuid=True), ForeignKey("incident_tickets.id"), nullable=True)

    # Résultat du tool MCP une fois exécuté (succès ou échec)
    result = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    requester = relationship("User", foreign_keys=[requested_by])
    confirmer = relationship("User", foreign_keys=[confirmed_by])
    incident_ticket = relationship("IncidentTicket", back_populates="action_requests")
    mcp_calls = relationship("MCPCall", back_populates="action_request")