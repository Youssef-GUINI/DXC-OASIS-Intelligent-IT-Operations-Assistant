"""Schémas des demandes échangées entre un ingénieur et l'administrateur."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.service_request import RequestDirection, RequestPriority, RequestStatus


class UserBrief(BaseModel):
    """Identité minimale d'un interlocuteur, suffisante pour l'affichage."""

    id: int
    email: str
    full_name: str | None = None
    role: str | None = None

    @classmethod
    def of(cls, user) -> "UserBrief | None":
        if user is None:
            return None
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.name if user.role else None,
        )


class RequestAttachmentOut(BaseModel):
    """Métadonnées d'un fichier joint — le binaire se récupère par sa route."""

    id: uuid.UUID
    filename: str
    content_type: str | None
    size_bytes: int
    uploader: UserBrief | None
    created_at: datetime


class ServiceRequestOut(BaseModel):
    id: uuid.UUID
    direction: RequestDirection
    title: str
    description: str | None
    request_type: str | None
    priority: RequestPriority
    status: RequestStatus
    creator: UserBrief | None
    assignee: UserBrief | None
    deadline: datetime | None
    administrator_response: str | None
    created_at: datetime
    updated_at: datetime
    # Date de la décision, quand elle a été prise : c'est elle que le détail
    # affiche à côté du statut « Approved » ou « Refused ».
    decided_at: datetime | None
    acknowledged_at: datetime | None
    completed_at: datetime | None
    # La liste se contente du nombre : afficher un trombone et un compteur ne
    # justifie pas de transporter les métadonnées de chaque fichier.
    attachment_count: int = 0


class ServiceRequestDetail(ServiceRequestOut):
    """Vue d'une demande seule : elle seule détaille les fichiers joints."""

    attachments: list[RequestAttachmentOut] = Field(default_factory=list)


class ServiceRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    # Facultative, conformément à la spécification.
    description: str | None = None
    request_type: str | None = Field(default=None, max_length=60)
    priority: RequestPriority = RequestPriority.MEDIUM
    # Échéance : n'a de sens que sur une demande envoyée par l'administrateur.
    deadline: datetime | None = None
    # Destinataire. Facultatif pour un ingénieur (l'administrateur est déduit),
    # obligatoire pour l'administrateur, qui choisit l'ingénieur destinataire.
    assigned_to: int | None = None


class ServiceRequestUpdate(BaseModel):
    """
    Correction d'une demande par son auteur.

    Tous les champs sont facultatifs : le service ne touche qu'à ceux
    réellement transmis (`exclude_unset`), pour qu'une interface qui n'envoie
    que le titre n'efface pas la description au passage. `None` reste donc un
    effacement volontaire, distinct de l'absence de champ.
    """

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    request_type: str | None = Field(default=None, max_length=60)
    priority: RequestPriority | None = None
    deadline: datetime | None = None


class RequestStatusUpdate(BaseModel):
    status: RequestStatus
    # Motif consigné dans le journal d'audit, sans être renvoyé au client.
    note: str | None = None
    # L'administrateur peut joindre sa réponse de synthèse au même appel.
    administrator_response: str | None = None
