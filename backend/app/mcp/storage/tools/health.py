"""
app/mcp/storage/tools/health.py

Tool d'agrégation pure : combine get_capacity + list_backups + get_dr_status
en une seule vue, sans aucun raisonnement LLM. Utilisé pour le tableau de
santé global (dashboard) et comme première étape de analyze_incident.

Ne contient pas de logique métier propre — importe les fonctions déjà
existantes des autres modules tools/*.py pour ne pas dupliquer la logique
de lecture disque / simulation.
"""

from app.mcp.storage.tools.capacity import get_capacity
from app.mcp.storage.tools.backup import list_backups
from app.mcp.storage.tools.disaster_recovery import get_dr_status

# Seuils d'alerte (point "Alertes intelligentes" du plan)
_DISK_ALERT_THRESHOLD_PERCENT = 90
_BACKUP_STALE_HOURS = 24
_RPO_DEFAULT_MINUTES = 60


def get_storage_health() -> dict:
    """
    Vue de santé globale : capacité, backups, réplication DR, et alertes
    calculées déterministiquement (pas par le LLM) à partir des seuils fixes.
    """
    capacity = get_capacity()
    backups = list_backups()
    dr_status = get_dr_status()

    alerts = []

    for volume in capacity.get("volumes", []):
        percent_used = volume.get("percent_used", 0)
        if percent_used >= _DISK_ALERT_THRESHOLD_PERCENT:
            alerts.append({
                "type": "disk_capacity",
                "severity": "critical" if percent_used >= 95 else "high",
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

    # get_dr_status() est censé retourner {"replicas": {volume_id: {...}}}.
    # Défensif : si la structure réelle diffère (clé différente, ou le dict
    # _SIMULATED_DR_STATUS est retourné tel quel sans wrapper), on s'adapte
    # plutôt que de planter — à ajuster une fois la vraie forme confirmée.
    replicas = dr_status.get("replicas")
    if replicas is None and all(isinstance(v, dict) for v in dr_status.values()):
        replicas = dr_status  # dr_status EST déjà le dict {volume_id: {...}}

    for replica_name, replica in (replicas or {}).items():
        lag = replica.get("replication_lag_minutes", 0)
        rpo = replica.get("rpo_target_minutes", _RPO_DEFAULT_MINUTES)
        if lag > rpo:
            alerts.append({
                "type": "rpo_breached",
                "severity": "high",
                "message": f"RPO dépassé pour {replica_name}: lag {lag}min > cible {rpo}min",
                "target": replica_name,
            })

    return {
        "capacity": capacity,
        "backups": backups,
        "dr_status": dr_status,
        "alerts": alerts,
        "overall_status": "critical" if any(a["severity"] == "critical" for a in alerts)
        else "warning" if alerts else "healthy",
    }