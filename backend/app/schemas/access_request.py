from datetime import datetime

from pydantic import BaseModel


class AccessRequestCreate(BaseModel):
    target_workspace: str
    reason: str


class AccessRequestResponse(BaseModel):
    id: int
    requested_by_id: int
    target_workspace: str
    reason: str | None
    status: str
    reviewed_by_id: int | None
    granted_token: str | None
    expires_at: datetime | None
    created_at: datetime
    reviewed_at: datetime | None

    class Config:
        from_attributes = True


class AccessRequestDecision(BaseModel):
    approve: bool
    review_note: str | None = None