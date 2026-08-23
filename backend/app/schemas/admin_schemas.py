from datetime import datetime

from pydantic import BaseModel


class RoleResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None
    action: str
    resource: str | None
    details: dict | None
    timestamp: datetime

    class Config:
        from_attributes = True