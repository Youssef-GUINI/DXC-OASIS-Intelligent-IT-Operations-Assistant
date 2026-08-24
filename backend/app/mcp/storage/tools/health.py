"""
app/mcp/storage/tools/health.py

Tool d'agrégation pure : combine get_capacity + list_backups en une seule vue,
sans aucun raisonnement LLM. Sert au dashboard et de première étape à
analyze_incident.

Les alertes sont calculées ici, de façon déterministe, à partir de seuils fixes
pour la capacité et de la cadence propre à chaque timer pour les sauvegardes —
jamais par le modèle.
"""

from concurrent.futures import ThreadPoolExecutor

from app.mcp.storage.tools.backup import list_backups
from app.mcp.storage.tools.capacity import get_capacity

_DISK_ALERT_THRESHOLD_PERCENT = 90
_DISK_CRITICAL_THRESHOLD_PERCENT = 95

# Un job est périmé quand il a dépassé sa propre cadence d'une demi-période :
# une sauvegarde quotidienne alerte à 36 h, une hebdomadaire à 10 j et demi.
# Un seuil unique de 24 h faisait alerter tous les jours `backup-restore-test`,
# hebdomadaire par construction, alors qu'il tournait exactement comme prévu.
_BACKUP_STALE_GRACE = 1.5

# Plancher, et repli quand la cadence est inconnue (timer monotone, VM qui n'a
# pas répondu). En deçà, l'âge du dernier point de restauration ne dit rien
# d'inquiétant : un job horaire en retard d'une heure n'est pas un incident.
_BACKUP_STALE_HOURS = 24


def stale_after_hours(job: dict) -> int:
    """Âge à partir duquel le dernier succès de ce job devient anormal."""
    interval = job.get("expected_interval_hours")
    if not interval:
        return _BACKUP_STALE_HOURS
    return max(int(interval * _BACKUP_STALE_GRACE), _BACKUP_STALE_HOURS)


def describe_interval(hours: int | None) -> str:
    """Cadence en clair, pour un message lu par un humain."""
    if not hours:
        return "on no fixed schedule"
    if hours % 168 == 0:
        weeks = hours // 168
        return "weekly" if weeks == 1 else f"every {weeks} weeks"
    if hours % 24 == 0:
        days = hours // 24
        return "daily" if days == 1 else f"every {days} days"
    return f"every {hours}h"


def get_storage_health() -> dict:
    """
    Vue de santé globale : capacité réelle, jobs de sauvegarde réels, et alertes
    dérivées des seuils ci-dessus.
    """
    # Les deux tools ouvrent chacun leur session SSH, et l'établissement de la
    # connexion domine le temps de réponse : enchaînés, ils coûtaient deux
    # poignées de main successives (~4 s) pour deux lectures indépendantes.
    with ThreadPoolExecutor(max_workers=2) as pool:
        capacity_task = pool.submit(get_capacity)
        backups_task = pool.submit(list_backups)
        capacity = capacity_task.result()
        backups = backups_task.result()

    alerts = []

    for volume in capacity.get("volumes", []):
        percent_used = volume.get("percent_used", 0)
        if percent_used >= _DISK_ALERT_THRESHOLD_PERCENT:
            alerts.append({
                "type": "disk_capacity",
                "severity": "critical" if percent_used >= _DISK_CRITICAL_THRESHOLD_PERCENT else "high",
                "message": f"Volume {volume.get('mountpoint')} at {percent_used}% usage",
                "target": volume.get("mountpoint"),
            })

    for job in backups.get("jobs", []):
        if job.get("status") == "failed":
            alerts.append({
                "type": "backup_failed",
                "severity": "high",
                "message": f"Backup job {job.get('job_id')} failed",
                "target": job.get("job_id"),
            })

        hours_ago = job.get("hours_since_last_success", 0)
        if hours_ago >= stale_after_hours(job):
            cadence = describe_interval(job.get("expected_interval_hours"))
            alerts.append({
                "type": "backup_stale",
                "severity": "medium",
                "message": (
                    f"{job.get('job_id')} runs {cadence} but last succeeded {hours_ago}h ago"
                ),
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
