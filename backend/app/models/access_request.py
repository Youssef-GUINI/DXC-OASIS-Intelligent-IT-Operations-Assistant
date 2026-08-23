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

    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    target_workspace = Column(String, nullable=False)

    reason = Column(Text, nullable=True)
    status = Column(Enum(AccessRequestStatus), default=AccessRequestStatus.PENDING, nullable=False)

    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    granted_token = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<AccessRequest status={self.status} target={self.target_workspace}>"