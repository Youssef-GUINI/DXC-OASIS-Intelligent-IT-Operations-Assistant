"""
Tool MCP : jobs de sauvegarde. Données SIMULÉES pour la V1.
"""
from datetime import datetime, timedelta, timezone

"""
À REMPLACER dans app/mcp/storage/tools/backup.py (fichier existant) :
la définition de _SIMULATED_JOBS, pour que "target" pointe vers les mêmes
volume_id que ceux de capacity.py (_SIMULATED_VOLUMES) et de
disaster_recovery.py (_SIMULATED_DR_STATUS).
"""

_SIMULATED_JOBS = {
    "job-db01-daily": {
        "target": "vol-prod-db01",
        "status": "failed",
        "error_code": "E-BKP-042",
        "last_run_hours_ago": 6,
        "last_success_hours_ago": 30,
    },
    "job-nas01-weekly": {
        "target": "vol-nas01",
        "status": "success",
        "error_code": None,
        "last_run_hours_ago": 18,
        "last_success_hours_ago": 18,
    },
    "job-app-daily": {
        "target": "vol-app01",
        "status": "success",
        "error_code": None,
        "last_run_hours_ago": 5,
        "last_success_hours_ago": 5,
    },
}
# À ajouter à côté de _SIMULATED_JOBS existant dans backup.py
_SIMULATED_JOB_LOGS = {
    "job-db01-daily": [
        {"ts": "02:14:03", "level": "ERROR", "code": "E-BKP-042",
         "message": "Backup repository write failed: insufficient space"},
        {"ts": "02:14:01", "level": "INFO", "message": "Starting incremental backup of /data/prod"},
        {"ts": "02:13:58", "level": "INFO", "message": "Snapshot taken, beginning transfer"},
    ],
    "job-nas01-weekly": [
        {"ts": "01:00:12", "level": "INFO", "message": "Backup completed successfully"},
    ],
    "job-app-daily": [
        {"ts": "03:05:44", "level": "INFO", "message": "Backup completed successfully"},
    ],
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


def get_backup_job_status(target: str | None = None) -> dict:
    """
    Retourne le statut détaillé d'un job de backup (ou de tous les jobs si
    target=None) : dernier run, statut, code d'erreur éventuel, ancienneté
    du dernier backup réussi.
    """
    now = datetime.utcnow()
    jobs = _SIMULATED_JOBS if target is None else {
        k: v for k, v in _SIMULATED_JOBS.items() if target in (k, v.get("target"))
    }

    result = []
    for job_id, job in jobs.items():
        last_success = job.get("last_success_hours_ago", 0)
        result.append({
            "job_id": job_id,
            "target": job.get("target"),
            "status": job.get("status"),
            "last_run": (now - timedelta(hours=job.get("last_run_hours_ago", 0))).isoformat(),
            "last_success_at": (now - timedelta(hours=last_success)).isoformat(),
            "hours_since_last_success": last_success,
            "error_code": job.get("error_code"),
        })
    return {"jobs": result}


def get_backup_logs(job_id: str, lines: int = 20) -> dict:
    """Retourne les dernières lignes de log d'un job de backup donné (simulé)."""
    logs = _SIMULATED_JOB_LOGS.get(job_id, [])
    return {"job_id": job_id, "logs": logs[:lines]}