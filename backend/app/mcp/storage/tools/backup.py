"""
app/mcp/storage/tools/backup.py

Lit les vrais jobs de sauvegarde de la VM Storage : timers systemd et l'état
des units qu'ils déclenchent, via SSH.

Aucune donnée simulée. Tant qu'aucun timer de sauvegarde n'existe sur la VM,
`list_backups()` renvoie une liste vide accompagnée de `configured: False` —
l'interface l'affiche honnêtement au lieu d'inventer des jobs.

Un timer est reconnu comme sauvegarde si son nom contient l'un des motifs de
`_BACKUP_NAME_PATTERNS`. Nommer un timer `backup-*.timer` suffit donc à le
faire apparaître ici.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from app.mcp.storage.ssh import StorageVMError, quote, run, run_many

_BACKUP_NAME_PATTERNS = ("backup", "sauvegarde", "restic", "borg", "borgmatic", "rsnapshot", "duplicity")

# `systemctl list-timers` : NEXT LEFT LAST PASSED UNIT ACTIVATES
_LAST_COLUMN = re.compile(r"^(?P<rest>.*?)\s+(?P<unit>\S+\.timer)\s+(?P<service>\S+)\s*$")


def _looks_like_backup(name: str) -> bool:
    lowered = name.lower()
    return any(pattern in lowered for pattern in _BACKUP_NAME_PATTERNS)


def _parse_timer_units(output: str) -> list[str]:
    """Extrait les noms de units .timer d'une sortie `systemctl list-timers`."""
    units = []
    for line in output.splitlines():
        match = _LAST_COLUMN.match(line.strip())
        if match and _looks_like_backup(match.group("unit")):
            units.append(match.group("unit"))
    return units


def _service_for(timer_unit: str) -> str:
    return timer_unit.rsplit(".", 1)[0] + ".service"


def _parse_show(output: str) -> dict[str, str]:
    """Parse une sortie `systemctl show -p Key=Value`."""
    properties: dict[str, str] = {}
    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            properties[key.strip()] = value.strip()
    return properties


def _hours_since(timestamp: str) -> int | None:
    """Convertit un horodatage systemd (microsecondes epoch) en heures écoulées."""
    try:
        microseconds = int(timestamp)
    except (TypeError, ValueError):
        return None
    if microseconds <= 0:
        return None
    moment = datetime.fromtimestamp(microseconds / 1_000_000, tz=timezone.utc)
    return max(int((datetime.now(timezone.utc) - moment).total_seconds() // 3600), 0)


def _job_from_properties(timer_unit: str, properties: dict[str, str]) -> dict:
    result = properties.get("Result", "")
    active_state = properties.get("ActiveState", "")
    sub_state = properties.get("SubState", "")

    if active_state == "activating" or sub_state == "running":
        status = "running"
    elif result == "success":
        status = "success"
    elif not result or result == "n/a":
        # Le service n'a encore jamais tourné : le timer est planifié, c'est tout.
        status = "scheduled"
    else:
        status = "failed"

    hours_since_run = _hours_since(properties.get("ExecMainStartTimestampUSec", ""))
    # systemd n'expose pas la date du dernier succès distincte du dernier run :
    # elle n'est connue que si ce dernier run a réussi. 0 signifie "inconnu",
    # ce que les seuils de health.py traitent comme non alarmant.
    hours_since_success = hours_since_run if status == "success" and hours_since_run else 0

    return {
        "job_id": timer_unit,
        "target": properties.get("Description") or _service_for(timer_unit),
        "status": status,
        "last_run": properties.get("ExecMainExitTimestamp") or None,
        "hours_since_last_success": hours_since_success,
        "error_code": result if status == "failed" else None,
    }


_SHOW_PROPERTIES = (
    "Description,ActiveState,SubState,Result,"
    "ExecMainStartTimestampUSec,ExecMainExitTimestamp"
)


def list_backups(target: str | None = None) -> dict:
    """
    Liste les jobs de sauvegarde réellement définis sur la VM.

    `configured: False` signifie qu'aucun timer de sauvegarde n'existe encore —
    ce n'est pas une erreur, juste une VM sur laquelle rien n'a été mis en place.
    """
    try:
        listing = run("systemctl list-timers --all --no-pager --no-legend", allow_failure=True)
        timer_units = _parse_timer_units(listing)

        if not timer_units:
            return {"jobs": [], "configured": False}

        commands = {
            unit: f"systemctl show {quote(_service_for(unit))} -p {_SHOW_PROPERTIES}"
            for unit in timer_units
        }
        raw = run_many(commands)
    except StorageVMError as error:
        return {"error": str(error), "jobs": []}

    jobs = []
    for unit, output in raw.items():
        job = _job_from_properties(unit, _parse_show(output))
        if target and target not in (job["job_id"], job["target"]):
            continue
        jobs.append(job)

    if target and not jobs:
        return {"error": f"No backup job named '{target}' on the VM", "jobs": []}

    return {"jobs": jobs, "configured": True}


def get_backup_job_status(target: str | None = None) -> dict:
    """Alias détaillé de list_backups — même source, même format."""
    return list_backups(target)


def run_backup(target: str) -> dict:
    """
    Déclenche immédiatement un job de sauvegarde existant.
    Action non destructive (ajout de données), pas de confirmation requise.
    """
    service = _service_for(target) if target.endswith(".timer") else target
    try:
        run(f"systemctl start {quote(service)}")
    except StorageVMError as error:
        return {"error": str(error), "action": "backup_failed", "target": target}

    return {"action": "backup_started", "target": service, "status": "running"}


def get_backup_logs(job_id: str, lines: int = 20) -> dict:
    """Dernières lignes de journal du job, lues via journalctl."""
    service = _service_for(job_id) if job_id.endswith(".timer") else job_id
    try:
        output = run(
            f"journalctl -u {quote(service)} -n {int(lines)} --no-pager -o short-iso",
            allow_failure=True,
        )
    except StorageVMError as error:
        return {"error": str(error), "job_id": job_id, "logs": []}

    return {
        "job_id": service,
        "logs": [{"line": line} for line in output.strip().splitlines() if line.strip()],
    }
