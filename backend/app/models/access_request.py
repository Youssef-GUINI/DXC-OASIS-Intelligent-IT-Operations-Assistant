"""
Modèle AccessRequest — représente une demande d'accès cross-domain
(ex: un Linux Engineer demandant un accès temporaire en lecture seule
au workspace Storage), conformément au "Cross-Domain Access Workflow"
de l'architecture de référence.

Types Integer pour rester cohérent avec User/Role (pas de UUID chez nous).
"""
import enum

from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import relationship

from app.database.base import Base


class AccessRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Qui demande, et vers quel workspace (texte libre pour l'instant :
    # "linux" ou "storage" — pas d'enum Workspace partagée pour éviter
    # une dépendance vers un fichier incident.py qui n'existe pas encore).
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    target_workspace = Column(String, nullable=False)

    reason = Column(Text, nullable=True)
    status = Column(Enum(AccessRequestStatus), default=AccessRequestStatus.PENDING, nullable=False)

    # Qui a validé/refusé (un admin), rempli seulement une fois traité
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    # Token temporaire généré si la demande est approuvée (lecture seule,
    # avec expiration) — utilisable plus tard pour appeler le MCP Server cible.
    granted_token = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<AccessRequest status={self.status} target={self.target_workspace}>"