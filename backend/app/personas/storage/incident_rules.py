"""
app/personas/storage/incident_rules.py

CORRECTIF : get_capacity() retourne {"volumes": [...]}  -- un dict qui
englobe une liste -- pas une liste brute ni un dict à plat représentant un
seul volume. L'ancienne version de evaluate_tool_result() ne gérait que
ces deux derniers cas, donc ne détectait jamais rien sur get_capacity.

_extract_items() gère maintenant explicitement ce format d'enveloppe.

check_backup_status est aligné sur le format réel renvoyé par backup.py
(lecture des timers systemd) : clés job_id / target / status / error_code.

La règle DR a été supprimée en même temps que disaster_recovery.py : aucune
réplication réelle n'existe sur la VM, et OASIS ne doit pas lever d'incident
sur une donnée qu'il ne mesure pas.
"""

from __future__ import annotations

from typing import Any, Optional

from app.models.incident_ticket import IncidentSeverity

CAPACITY_WARNING_THRESHOLD = 85
CAPACITY_CRITICAL_THRESHOLD = 95

# Clés connues sous lesquelles un résultat de tool peut envelopper sa
# liste d'éléments. Complétez cette liste au fur et à mesure que d'autres
# tools MCP réels sont inspectés.
_KNOWN_LIST_WRAPPER_KEYS = ("volumes", "jobs", "backups", "snapshots")


def _extract_items(tool_result: Any) -> list[dict]:
    """
    Normalise un résultat de tool MCP en liste de dicts exploitables,
    quel que soit le format d'enveloppe utilisé par le tool réel :
      - liste brute                         -> telle quelle
      - dict englobant une liste connue      -> la liste dépaquetée
      - dict représentant un seul objet      -> [ce dict]
      - autre chose (str d'erreur, etc.)     -> []
    """
    if isinstance(tool_result, list):
        return [item for item in tool_result if isinstance(item, dict)]

    if isinstance(tool_result, dict):
        for key in _KNOWN_LIST_WRAPPER_KEYS:
            value = tool_result.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        # Pas de clé d'enveloppe connue : soit un dict à plat représentant
        # un seul objet, soit un dict d'erreur (ex: {"error": "..."})
        # -- dans ce dernier cas, les check_* ne trouveront pas les clés
        # attendues et renverront naturellement None, sans planter.
        return [tool_result]

    return []


def check_capacity(volume: dict[str, Any]) -> Optional[dict]:
    percent = volume.get("percent_used")
    if percent is None:
        return None

    if percent >= CAPACITY_CRITICAL_THRESHOLD:
        severity = IncidentSeverity.CRITICAL
    elif percent >= CAPACITY_WARNING_THRESHOLD:
        severity = IncidentSeverity.HIGH
    else:
        return None

    mountpoint = volume.get("mountpoint", "?")
    volume_id = volume.get("volume_id", mountpoint)
    return {
        "title": f"Volume {volume_id} à {percent}% de capacité",
        "description": (
            f"Le volume {volume_id} ({volume.get('device', '?')}) monté sur "
            f"{mountpoint} a atteint {percent}% d'utilisation "
            f"({volume.get('used_gb', '?')}/{volume.get('total_gb', '?')} Go)."
        ),
        "severity": severity,
        "affected_system": volume_id,
        "impact_summary": f"{percent}% d'utilisation disque sur {volume_id}.",
        "mcp_data": volume,
        "recommendations": [
            {
                "order": 1,
                "description": f"Vérifier les snapshots anciens sur {volume_id} pouvant être purgés",
                "action_type": None,
                "target": volume_id,
                "requires_confirmation": False,
            }
        ],
    }


def check_backup_status(job: dict[str, Any]) -> Optional[dict]:
    """Aligné sur le format réel de backup.py (timers systemd)."""
    if job.get("status") != "failed":
        return None

    name = job.get("job_id", "?")
    target = job.get("target", name)
    error_code = job.get("error_code")
    detail = f" (résultat systemd : {error_code})" if error_code else ""

    return {
        "title": f"Échec du job de sauvegarde {name}",
        "description": f"Le job {name} ciblant {target} a échoué{detail}.",
        "severity": IncidentSeverity.HIGH,
        "affected_system": target,
        "impact_summary": f"Dernier backup en échec pour {target}.",
        "mcp_data": job,
        "recommendations": [
            {
                "order": 1,
                "description": f"Consulter le journal du job avec get_backup_logs sur {name}",
                "action_type": None,
                "target": name,
                "requires_confirmation": False,
            },
            {
                "order": 2,
                "description": f"Relancer le job de sauvegarde {name}",
                "action_type": "run_backup",
                "target": name,
                "requires_confirmation": False,
            },
        ],
    }


_RULES_BY_TOOL = {
    "get_capacity": check_capacity,
    "list_backups": check_backup_status,
    "get_backup_job_status": check_backup_status,
}


def evaluate_tool_result(tool_name: str, tool_result: Any) -> list[dict]:
    rule = _RULES_BY_TOOL.get(tool_name)
    if rule is None:
        return []

    detected: list[dict] = []
    for item in _extract_items(tool_result):
        result = rule(item)
        if result is not None:
            detected.append(result)
    return detected