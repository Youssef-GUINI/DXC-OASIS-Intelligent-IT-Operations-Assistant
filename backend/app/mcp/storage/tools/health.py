"""
app/mcp/storage/tools/health.py

Tool d'agrégation pure : combine get_capacity + list_backups en une seule vue,
sans aucun raisonnement LLM. Sert au dashboard et de première étape à
analyze_incident.

Les alertes sont calculées ici, de façon déterministe, à partir de seuils fixes
— jamais par le modèle.
"""

from app.mcp.storage.tools.backup import list_backups
from app.mcp.storage.tools.capacity import get_capacity

_DISK_ALERT_THRESHOLD_PERCENT = 90
_DISK_CRITICAL_THRESHOLD_PERCENT = 95
_BACKUP_STALE_HOURS = 24


def get_storage_health() -> dict:
    """
    Vue de santé globale : capacité réelle, jobs de sauvegarde réels, et alertes
    dérivées des seuils ci-dessus.
    """
    capacity = get_capacity()
    backups = list_backups()

    alerts = []

    for volume in capacity.get("volumes", []):
        percent_used = volume.get("percent_used", 0)
        if percent_used >= _DISK_ALERT_THRESHOLD_PERCENT:
            alerts.append({
                "type": "disk_capacity",
                "severity": "critical" if percent_used >= _DISK_CRITICAL_THRESHOLD_PERCENT else "high",
                "message": f"Volume {volume.get('mountpoint')} à {percent_used}% d'utilisation",
                "target": volume.get("mountpoint"),
            })

    for job in backups.get("jobs", []):
        if job.get("status") == "failed":
            alerts.append({
                "type": "backup_failed",
                "severity": "high",
                "message": f"Job {job.get('job_id')} en échec",
                "target": job.get("job_id"),
            })

        hours_ago = job.get("hours_since_last_success", 0)
        if hours_ago >= _BACKUP_STALE_HOURS:
            alerts.append({
                "type": "backup_stale",
                "severity": "medium",
                "message": f"Dernier backup réussi il y a {hours_ago}h pour {job.get('job_id')}",
                "target": job.get("job_id"),
            })

    if capacity.get("error"):
        overall_status = "unknown"
    elif any(alert["severity"] == "critical" for alert in alerts):
        overall_status = "critical"
    elif alerts:
        overall_status = "warning"
    else:
        overall_status = "healthy"

    return {
        "capacity": capacity,
        "backups": backups,
        "alerts": alerts,
        "overall_status": overall_status,
    }
