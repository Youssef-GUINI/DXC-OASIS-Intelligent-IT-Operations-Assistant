from pydantic import BaseModel


class LinuxKPIs(BaseModel):
    total_incidents: int
    open_incidents: int
    resolved_incidents: int
    avg_resolution_minutes: float | None
    incidents_by_category: dict[str, int]
    incidents_by_severity: dict[str, int]
    incidents_by_source: dict[str, int]