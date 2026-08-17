"""
app/models/knowledge_document.py

Document ajouté volontairement par un ingénieur via le Data Hub, pour
enrichir la base de connaissances qu'OASIS interroge (RAG).

Le fichier lui-même vit sur disque (settings.upload_dir) ; cette table ne
garde que les métadonnées et l'état d'indexation Chroma.
"""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.base import Base


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)

    # Collection Chroma cible — "storage_kb" pour la persona Storage.
    collection = Column(String, nullable=False, default="storage_kb", index=True)
    chunk_count = Column(Integer, nullable=False, default=0)

    status = Column(Enum(DocumentStatus), nullable=False, default=DocumentStatus.PENDING)
    error = Column(Text, nullable=True)

    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    indexed_at = Column(DateTime(timezone=True), nullable=True)

    uploader = relationship("User")
