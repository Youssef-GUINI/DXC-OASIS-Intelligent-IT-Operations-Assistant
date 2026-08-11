"""
Tool MCP : jobs de sauvegarde. Données SIMULÉES pour la V1.
"""
from datetime import datetime, timedelta, timezone

_SIMULATED_JOBS = {
    "job-db01-daily": {"target": "vol-prod-db01", "status": "success", "hours_ago": 6},
    "job-nas01-weekly": {"target": "vol-backup-nas01", "status": "failed", "hours_ago": 30},
    "job-app-daily": {"target": "vol-app-storage", "status": "success", "hours_ago": 5},
}


def list_backups(target: str | None = None) -> dict:
    """Liste les jobs de sauvegarde, éventuellement filtrés par volume cible."""
    now = datetime.now(timezone.utc)
    jobs = []
    for job_id, job in _SIMULATED_JOBS.items():
        if target and job["target"] != target:
            continue
        last_run = now - timedelta(hours=job["hours_ago"])
        jobs.append({
            "job_id": job_id,
            "target": job["target"],
            "status": job["status"],
            "last_run": last_run.isoformat(),
        })

    if target and not jobs:
        return {"error": f"Aucun job de sauvegarde connu pour la cible '{target}'"}

    return {"jobs": jobs}


def run_backup(target: str) -> dict:
    """
    Déclenche une sauvegarde immédiate d'un volume.
    Action non destructive (ajout de données), donc pas de confirmation
    requise contrairement à restore.py et disaster_recovery.py.
    """
    return {
        "action": "backup_started",
        "target": target,
        "job_id": f"job-manual-{target}",
        "status": "running",
    }