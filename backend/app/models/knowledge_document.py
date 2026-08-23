from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database.base import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    collection = Column(String(50), nullable=False)  # "linux_kb"
    size_bytes = Column(Integer, nullable=False)
    chunk_count = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="indexed")  # "indexed" ou "failed"
    error = Column(Text, nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    indexed_at = Column(DateTime(timezone=True), nullable=True)

    uploaded_by = relationship("User")