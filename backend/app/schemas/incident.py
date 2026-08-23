from datetime import datetime
from pydantic import BaseModel, computed_field

# Seuil a partir duquel un incident est considere comme "recurrent".
RECURRENCE_THRESHOLD = 3


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
    started_by_id: int | None
    started_at: datetime | None
    recurrence_count: int
    created_at: datetime
    resolved_at: datetime | None

    @computed_field
    @property
    def requires_manual_resolution(self) -> bool:
        return self.severity == "critical" and self.status == "open"

    @computed_field
    @property
    def is_recurring(self) -> bool:
        return self.recurrence_count >= RECURRENCE_THRESHOLD

    class Config:
        from_attributes = True