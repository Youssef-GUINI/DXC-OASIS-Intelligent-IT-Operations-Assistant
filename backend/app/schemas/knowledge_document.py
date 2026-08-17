"""Schémas du Data Hub."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.knowledge_document import DocumentStatus


class KnowledgeDocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str | None
    size_bytes: int
    collection: str
    chunk_count: int
    status: DocumentStatus
    error: str | None
    created_at: datetime
    indexed_at: datetime | None

    class Config:
        from_attributes = True
