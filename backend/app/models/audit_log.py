from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship

from app.database.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User")

    action = Column(String, nullable=False)
    resource = Column(String, nullable=True)
    details = Column(JSON, nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<AuditLog action={self.action}>"