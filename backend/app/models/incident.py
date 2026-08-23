from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database.base import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    persona = Column(String(50), nullable=False)
    source = Column(String(20), nullable=False, default="user")
    severity = Column(String(20), nullable=True)
    category = Column(String(30), nullable=True)
    status = Column(String(20), nullable=False, default="open")
    user_message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    diagnosis = Column(Text, nullable=True)
    started_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    # Nombre d'incidents de la meme categorie (persona + category + source="system")
    # survenus dans les 24h precedant celui-ci, lui compris. Calcule une seule
    # fois a la creation (voir incident_detector.py) plutot qu'a chaque lecture.
    recurrence_count = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    started_by = relationship("User", foreign_keys=[started_by_id])