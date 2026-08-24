"""
app/models/service_request.py

Demandes échangées entre un ingénieur et l'administrateur, dans les deux sens.

À ne pas confondre avec les deux autres modèles au nom proche :
  - AccessRequest sert au workflow cross-domain (obtenir un accès temporaire
    à un autre workspace) ;
  - ActionRequest encadre l'exécution d'une action MCP destructive et n'a de
    sens que couplé à un outil.

ServiceRequest ne déclenche aucune action technique : c'est un canal de
communication humain. L'interface en montre l'essentiel — la demande, la
réponse de l'administrateur, et l'horodatage de la décision.

Les deux tables satellites ne sont plus exposées par l'API : RequestEvent
reste alimentée comme journal d'audit côté serveur, RequestMessage n'est
conservée que pour les fils déjà enregistrés avant le retrait du chat.

Le sens de circulation est porté par `direction` plutôt que par deux tables :
les champs sont les mêmes, seuls le vocabulaire d'interface et les
transitions de statut autorisées diffèrent (voir services/request_service).
"""

import enum
import uuid

from sqlalchemy import (
    BigInteger, Column, DateTime, Enum, ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.base import Base


class RequestDirection(str, enum.Enum):
    ENGINEER_TO_ADMIN = "engineer_to_admin"
    ADMIN_TO_ENGINEER = "admin_to_engineer"


class RequestPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequestStatus(str, enum.Enum):
    # Communs aux deux sens
    PENDING = "pending"
    COMPLETED = "completed"
    # Traitement d'une demande recue par l'administrateur
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    # Traitement d'une demande recue par l'ingenieur
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    direction = Column(Enum(RequestDirection), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    # Facultative : l'interface accepte une demande sans description.
    description = Column(Text, nullable=True)
    request_type = Column(String(60), nullable=True)
    priority = Column(Enum(RequestPriority), nullable=False, default=RequestPriority.MEDIUM)
    status = Column(Enum(RequestStatus), nullable=False, default=RequestStatus.PENDING, index=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Propre aux demandes envoyees par l'administrateur.
    deadline = Column(DateTime(timezone=True), nullable=True)

    # Reponse de synthese de l'administrateur, distincte du fil de discussion :
    # c'est elle qui s'affiche dans la liste, sans ouvrir le detail.
    administrator_response = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )
    # Horodatage de la decision (approuvee ou refusee). Distinct de updated_at,
    # qui bouge a chaque changement ulterieur : le detail annonce « refusee le
    # ... », pas « modifiee le ... ».
    decided_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to])

    messages = relationship(
        "RequestMessage",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="RequestMessage.created_at",
    )
    events = relationship(
        "RequestEvent",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="RequestEvent.created_at",
    )
    attachments = relationship(
        "RequestAttachment",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="RequestAttachment.created_at",
    )


class RequestMessage(Base):
    """
    Un message du fil de discussion attache a une demande.

    Historique : le fil a ete retire de l'interface et de l'API. La table est
    conservee pour ne pas detruire les echanges deja enregistres, mais plus
    rien n'y ecrit.
    """

    __tablename__ = "request_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(
        UUID(as_uuid=True), ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    request = relationship("ServiceRequest", back_populates="messages")
    author = relationship("User")


class RequestEvent(Base):
    """
    Journal des changements de statut.

    Ecrit a chaque transition et jamais renvoye au client : l'interface se
    contente du statut courant et de son horodatage. Sert de piste d'audit et
    de source de reprise (c'est lui qui a permis de retro-remplir
    ServiceRequest.decided_at).
    """

    __tablename__ = "request_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(
        UUID(as_uuid=True), ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    from_status = Column(Enum(RequestStatus), nullable=True)
    to_status = Column(Enum(RequestStatus), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    request = relationship("ServiceRequest", back_populates="events")
    actor = relationship("User")


class RequestAttachment(Base):
    """
    Un fichier joint a une demande : le rapport demande, une capture, un
    export de metriques.

    Comme dans le Data Hub, le fichier vit sur disque et le nom fourni par le
    client ne sert jamais a construire un chemin -- le fichier est ecrit sous
    l'UUID de la ligne. Le nom d'origine ne survit que comme metadonnee, ce
    qui rend toute traversee de repertoire impossible.
    """

    __tablename__ = "request_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(
        UUID(as_uuid=True), ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    filename = Column(String(255), nullable=False)
    stored_path = Column(String, nullable=False)
    content_type = Column(String(120), nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    request = relationship("ServiceRequest", back_populates="attachments")
    uploader = relationship("User")
