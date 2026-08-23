from datetime import datetime
from pydantic import BaseModel, field_validator


class KnowledgeDocumentResponse(BaseModel):
    id: str
    filename: str
    content_type: str | None
    size_bytes: int
    collection: str
    chunk_count: int
    status: str
    error: str | None
    created_at: datetime
    indexed_at: datetime | None

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_to_str(cls, value):
        return str(value)

    class Config:
        from_attributes = True


class DocumentContentResponse(BaseModel):
    filename: str
    text: str