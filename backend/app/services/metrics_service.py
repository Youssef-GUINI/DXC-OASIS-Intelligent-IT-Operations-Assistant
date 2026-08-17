"""
app/services/metrics_service.py

Collecte et lecture des métriques de performance disque réelles.

`collect_once()` prélève un échantillon sur la VM et l'enregistre. Il est
appelé périodiquement par la tâche de fond démarrée dans main.py, et peut
aussi être déclenché manuellement.

`read_series()` relit l'historique enregistré. Il ne génère jamais de points :
tant que le collecteur n'a pas tourné, la série est vide et l'interface le dit.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, literal_column
from sqlalchemy.orm import Session

from app.mcp.storage.tools.performance import sample_disk_performance
from app.models.metric import DiskMetric

# Fenêtre couverte et granularité d'agrégation de chaque plage.
RANGE_WINDOWS = {
    "24h": (timedelta(hours=24), timedelta(hours=1)),
    "7d": (timedelta(days=7), timedelta(hours=6)),
    "30d": (timedelta(days=30), timedelta(days=1)),
}

# Au-delà, les échantillons ne servent plus aucune plage affichable.
RETENTION = timedelta(days=31)


def collect_once(db: Session) -> dict:
    """
    Prélève un échantillon par device et l'enregistre.
    Retourne un compte-rendu, jamais une exception : le collecteur tourne en
    tâche de fond et ne doit pas s'arrêter parce que la VM est éteinte.
    """
    sample = sample_disk_performance()
    if sample.get("error"):
        return {"recorded": 0, "error": sample["error"]}

    for device, rates in sample["devices"].items():
        db.add(
            DiskMetric(
                device=device,
                iops=rates["iops"],
                throughput_mbps=rates["throughput_mbps"],
                latency_ms=rates["latency_ms"],
            )
        )
    db.commit()

    return {"recorded": len(sample["devices"]), "devices": list(sample["devices"])}


def purge_old(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - RETENTION
    deleted = db.query(DiskMetric).filter(DiskMetric.recorded_at < cutoff).delete()
    db.commit()
    return deleted


def read_series(db: Session, range_key: str = "24h") -> dict:
    """
    Agrège les échantillons enregistrés en une série lisible.

    Les devices sont additionnés (IOPS et débit) ou moyennés (latence) par
    intervalle : le graphique montre la charge de la VM, pas d'un disque isolé.
    """
    window, bucket = RANGE_WINDOWS.get(range_key, RANGE_WINDOWS["24h"])
    since = datetime.now(timezone.utc) - window

    # date_bin (PostgreSQL 14+) regroupe par intervalle de largeur fixe côté
    # base. La largeur vient de RANGE_WINDOWS, jamais de l'utilisateur.
    bucket_expression = func.date_bin(
        literal_column(f"interval '{int(bucket.total_seconds())} seconds'"),
        DiskMetric.recorded_at,
        literal_column("timestamptz '1970-01-01'"),
    )

    # Deux étapes : on moyenne d'abord par device sur l'intervalle, puis on
    # additionne les devices. Agréger en une seule passe donnerait un total
    # faussé dès qu'un device a plus d'échantillons qu'un autre.
    per_device = (
        db.query(
            bucket_expression.label("bucket"),
            DiskMetric.device.label("device"),
            func.avg(DiskMetric.iops).label("iops"),
            func.avg(DiskMetric.throughput_mbps).label("throughput_mbps"),
            func.avg(DiskMetric.latency_ms).label("latency_ms"),
        )
        .filter(DiskMetric.recorded_at >= since)
        .group_by("bucket", DiskMetric.device)
        .subquery()
    )

    rows = (
        db.query(
            per_device.c.bucket,
            func.sum(per_device.c.iops).label("iops"),
            func.sum(per_device.c.throughput_mbps).label("throughput_mbps"),
            func.avg(per_device.c.latency_ms).label("latency_ms"),
        )
        .group_by(per_device.c.bucket)
        .order_by(per_device.c.bucket)
        .all()
    )

    points = [
        {
            "timestamp": row.bucket,
            "iops": round(float(row.iops), 2),
            "throughput_mbps": round(float(row.throughput_mbps), 2),
            "latency_ms": round(float(row.latency_ms), 2),
        }
        for row in rows
    ]

    def average(key: str) -> float:
        if not points:
            return 0.0
        return round(sum(point[key] for point in points) / len(points), 2)

    half = len(points) // 2
    recent = points[half:]
    earlier = points[:half]
    trend = 0.0
    if earlier and recent:
        earlier_average = sum(point["iops"] for point in earlier) / len(earlier)
        recent_average = sum(point["iops"] for point in recent) / len(recent)
        if earlier_average:
            trend = round((recent_average - earlier_average) / earlier_average * 100, 1)

    return {
        "range": range_key,
        "points": points,
        "iops_avg": average("iops"),
        "throughput_avg_mbps": average("throughput_mbps"),
        "latency_avg_ms": average("latency_ms"),
        "iops_trend_percent": trend,
    }
