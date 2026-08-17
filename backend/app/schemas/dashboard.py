"""Schémas de sortie du dashboard Storage."""

from datetime import datetime

from pydantic import BaseModel


class VolumeOut(BaseModel):
    volume_id: str | None
    mountpoint: str | None
    device: str | None
    filesystem: str | None
    total_gb: float
    used_gb: float
    available_gb: float
    percent_used: int
    status: str


class CapacityOut(BaseModel):
    total_gb: float
    used_gb: float
    available_gb: float
    reserved_gb: float
    percent_used: float
    volumes: list[VolumeOut]
    volumes_near_limit: int
    unavailable: bool
    error: str | None


class BackupJobOut(BaseModel):
    job_id: str | None
    target: str | None
    status: str
    last_run: str | None
    hours_since_last_success: int


class BackupsOut(BaseModel):
    successful: int
    failed: int
    running: int
    scheduled: int
    total: int
    jobs: list[BackupJobOut]
    # False : aucun timer de sauvegarde n'existe encore sur la VM.
    configured: bool
    # Renseigné uniquement si la VM n'a pas pu être interrogée.
    error: str | None = None


class IncidentCountsOut(BaseModel):
    open: int
    by_severity: dict[str, int]
    needs_attention: int
    resolved_last_7d: int


class AlertOut(BaseModel):
    type: str
    severity: str
    message: str
    target: str | None


class OverviewOut(BaseModel):
    overall_status: str
    headline: str
    # None quand la VM est injoignable : le score n'a pas pu être mesuré.
    health_score: float | None
    capacity: CapacityOut
    backups: BackupsOut
    incidents: IncidentCountsOut
    alerts: list[AlertOut]
    generated_at: datetime


class PerformancePoint(BaseModel):
    timestamp: datetime
    iops: int
    throughput_mbps: float
    latency_ms: float


class PerformanceOut(BaseModel):
    range: str
    points: list[PerformancePoint]
    iops_avg: float
    throughput_avg_mbps: float
    latency_avg_ms: float
    iops_trend_percent: float
    # True : le collecteur n'a pas encore enregistré de mesure sur cette plage.
    collecting: bool


class ActivityItem(BaseModel):
    id: str
    kind: str
    title: str
    resource: str | None
    status: str
    severity: str | None
    timestamp: datetime


class InsightOut(BaseModel):
    id: str
    priority: str
    title: str
    detail: str
    action_label: str | None
    action_target: str | None
