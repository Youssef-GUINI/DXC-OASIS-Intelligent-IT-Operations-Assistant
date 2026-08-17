"""
app/models/mcp_call.py

Modèle d'audit pour tracer chaque appel d'outil MCP effectué par un persona
(Storage, Linux, ...), quel que soit le résultat.

Objectif : pouvoir prouver, a posteriori, qu'une réponse de l'agent s'appuie
bien sur un résultat MCP réel (et non inventé), et tracer qui a demandé quoi.
"""

import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database.base import Base  # adapter selon l'emplacement réel de Base


class MCPCallStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    DENIED = "denied"  # ex: garde-fou destructif a bloqué l'appel (confirm=False)


class MCPCall(Base):
    __tablename__ = "mcp_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Qui a déclenché l'appel (l'utilisateur final, pas le LLM).
    # CORRIGÉ : Integer -- users.id est un Integer, pas un UUID, même
    # incompatibilité que celle déjà corrigée sur IncidentTicket.created_by.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Domaine du persona à l'origine de l'appel : "storage", "linux", ...
    persona = Column(String, nullable=False, index=True)

    # Nom exact du tool MCP appelé (ex: "get_capacity", "restore_from_backup")
    tool_name = Column(String, nullable=False, index=True)

    # Arguments réellement envoyés au tool (après normalisation et garde-fou,
    # donc reflète le confirm=True/False réel, pas ce que le LLM avait proposé)
    arguments = Column(JSONB, nullable=False, default=dict)

    # Résultat brut renvoyé par le serveur MCP (avant reformulation par Groq)
    result = Column(JSONB, nullable=True)

    status = Column(Enum(MCPCallStatus), nullable=False, default=MCPCallStatus.SUCCESS)

    # Message d'erreur si status == FAILED
    error_message = Column(Text, nullable=True)

    # Lien optionnel vers une ActionRequest (confirmation d'action sensible),
    # nullable car la plupart des appels (get_capacity, list_backups...) ne
    # passent jamais par le circuit de confirmation
    action_request_id = Column(
        UUID(as_uuid=True), ForeignKey("action_requests.id"), nullable=True, index=True
    )

    # Regroupe les appels d'une même analyse d'incident (ex: analyze_incident
    # qui enchaîne get_backup_job_status -> get_capacity -> get_replication_status)
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
    action_request = relationship("ActionRequest", back_populates="mcp_calls", foreign_keys=[action_request_id])