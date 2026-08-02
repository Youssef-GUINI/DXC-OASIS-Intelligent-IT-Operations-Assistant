"""
Schémas Pydantic pour le workflow cross-domain — forme des données
acceptées en entrée et renvoyées en sortie des routes.
"""
from datetime import datetime

from pydantic import BaseModel


class AccessRequestCreate(BaseModel):
    """Ce qu'un utilisateur envoie pour demander un accès cross-domain."""
    target_workspace: str  # "linux" ou "storage"
    reason: str


class AccessRequestResponse(BaseModel):
    id: int
    requested_by_id: int
    target_workspace: str
    reason: str | None
    status: str
    reviewed_by_id: int | None
    granted_token: str | None
    expires_at: datetime | None
    created_at: datetime
    reviewed_at: datetime | None

    class Config:
        from_attributes = True


class AccessRequestDecision(BaseModel):
    """Ce qu'un admin envoie pour approuver ou refuser une demande."""
    approve: bool
    review_note: str | None = None