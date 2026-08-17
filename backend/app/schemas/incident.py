from datetime import datetime
from pydantic import BaseModel


class IncidentResponse(BaseModel):
    id: int
    persona: str
    source: str
    severity: str | None
    category: str | None
    status: str
    user_message: str
    response: str
    diagnosis: str | None
    created_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True