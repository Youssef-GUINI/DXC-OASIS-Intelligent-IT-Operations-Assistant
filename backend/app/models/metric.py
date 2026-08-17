"""
app/models/metric.py

Point de mesure de performance disque, prélevé sur la VM Storage.

Une ligne = un échantillon, pour un device, à un instant donné. Le graphique
Storage Performance lit cette table : l'historique 24h/7j/30j se construit au
fil des prélèvements, il n'est jamais fabriqué.
"""

import uuid

from sqlalchemy import Column, DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class DiskMetric(Base):
    __tablename__ = "disk_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Device tel que nommé par /proc/diskstats (sda, dm-0, nvme0n1…)
    device = Column(String, nullable=False, index=True)

    # Valeurs dérivées de deux lectures successives de /proc/diskstats.
    iops = Column(Float, nullable=False)
    throughput_mbps = Column(Float, nullable=False)
    latency_ms = Column(Float, nullable=False)

    recorded_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
