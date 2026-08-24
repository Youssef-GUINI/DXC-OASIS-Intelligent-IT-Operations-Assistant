"""
app/dashboard/kpi_service.py

Agrège les données du dashboard Storage Engineer à partir de deux sources :
  - les tools MCP storage (capacité réelle via SSH, backups, DR)
  - la base OASIS (tickets d'incident, demandes d'action)

Aucun appel LLM ici : le dashboard doit rester rapide et déterministe.
Les phrases destinées à l'utilisateur sont construites côté backend pour que
le frontend n'ait aucune règle métier à dupliquer.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.mcp.storage.tools.health import (
    describe_interval,
    get_storage_health,
    stale_after_hours,
)
from app.models.action_request import ActionRequest
from app.models.incident_ticket import IncidentSeverity, IncidentStatus, IncidentTicket
from app.services import metrics_service

CAPACITY_WARNING_PERCENT = 80
CAPACITY_CRITICAL_PERCENT = 90

_OPEN_STATUSES = (IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS)

# get_storage_health() ouvre deux connexions SSH vers la VM Storage : la
# réponse met plusieurs secondes, et le dashboard la demandait à chaque
# affichage -- c'est ce qui rendait le changement de page si lent.
#
# On sert donc toujours le dernier relevé connu, et on en redemande un en
# arrière-plan dès qu'il a dépassé cet âge. La page s'affiche immédiatement
# avec une donnée d'au plus une minute, au lieu d'attendre la VM ; seul le
# tout premier appel, quand rien n'a encore été relevé, doit patienter.
_HEALTH_FRESH_SECONDS = 60
_health_cache: tuple[float, datetime, dict] | None = None
_health_lock = threading.Lock()
_refresh_lock = threading.Lock()

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Capacité
# --------------------------------------------------------------------------

def _volume_status(percent_used: int) -> str:
    if percent_used >= CAPACITY_CRITICAL_PERCENT:
        return "critical"
    if percent_used >= CAPACITY_WARNING_PERCENT:
        return "warning"
    return "healthy"


def _build_capacity(raw_capacity: dict) -> dict:
    """Totalise les volumes remontés par `df` et enrichit chacun d'un statut."""
    error = raw_capacity.get("error")
    volumes = []

    for volume in raw_capacity.get("volumes", []):
        percent_used = int(volume.get("percent_used", 0))
        volumes.append({
            "volume_id": volume.get("volume_id"),
            "mountpoint": volume.get("mountpoint"),
            "device": volume.get("device"),
            "filesystem": volume.get("filesystem"),
            "total_gb": volume.get("total_gb", 0),
            "used_gb": volume.get("used_gb", 0),
            "available_gb": volume.get("available_gb", 0),
            "percent_used": percent_used,
            "status": _volume_status(percent_used),
        })

    total_gb = round(sum(v["total_gb"] for v in volumes), 1)
    used_gb = round(sum(v["used_gb"] for v in volumes), 1)
    available_gb = round(sum(v["available_gb"] for v in volumes), 1)
    # `df` ne rend pas total == used + available : la différence correspond aux
    # blocs réservés au superutilisateur.
    reserved_gb = round(max(total_gb - used_gb - available_gb, 0), 1)
    percent_used = round(used_gb / total_gb * 100, 1) if total_gb else 0

    return {
        "total_gb": total_gb,
        "used_gb": used_gb,
        "available_gb": available_gb,
        "reserved_gb": reserved_gb,
        "percent_used": percent_used,
        "volumes": volumes,
        "volumes_near_limit": sum(1 for v in volumes if v["status"] != "healthy"),
        "unavailable": bool(error),
        "error": error,
    }


# --------------------------------------------------------------------------
# Backups
# --------------------------------------------------------------------------

def _build_backups(raw_backups: dict) -> dict:
    jobs = []
    counts = {"successful": 0, "failed": 0, "running": 0, "scheduled": 0}

    for job in raw_backups.get("jobs", []):
        status = job.get("status", "scheduled")
        key = {"success": "successful"}.get(status, status)
        if key in counts:
            counts[key] += 1
        jobs.append({
            "job_id": job.get("job_id"),
            "target": job.get("target"),
            "status": status,
            "last_run": job.get("last_run"),
            "hours_since_last_success": job.get("hours_since_last_success", 0),
            "expected_interval_hours": job.get("expected_interval_hours"),
        })

    return {
        **counts,
        "total": len(jobs),
        "jobs": jobs,
        # False = aucun timer de sauvegarde n'existe encore sur la VM. Distinct
        # de `error`, qui signifie que la VM n'a pas pu être interrogée.
        "configured": bool(raw_backups.get("configured", False)),
        "error": raw_backups.get("error"),
    }


# --------------------------------------------------------------------------
# Incidents
# --------------------------------------------------------------------------

def _build_incidents(db: Session) -> dict:
    rows = (
        db.query(IncidentTicket.severity, func.count(IncidentTicket.id))
        .filter(IncidentTicket.status.in_(_OPEN_STATUSES))
        .group_by(IncidentTicket.severity)
        .all()
    )
    by_severity = {severity.value: 0 for severity in IncidentSeverity}
    for severity, count in rows:
        by_severity[severity.value] = count

    resolved_last_7d = (
        db.query(func.count(IncidentTicket.id))
        .filter(
            IncidentTicket.status == IncidentStatus.RESOLVED,
            IncidentTicket.resolved_at >= datetime.now(timezone.utc) - timedelta(days=7),
        )
        .scalar()
    ) or 0

    return {
        "open": sum(by_severity.values()),
        "by_severity": by_severity,
        "needs_attention": by_severity["critical"] + by_severity["high"],
        "resolved_last_7d": resolved_last_7d,
    }


# --------------------------------------------------------------------------
# Score de santé et phrase d'accroche
# --------------------------------------------------------------------------

_ALERT_WEIGHTS = {"critical": 12, "high": 6, "medium": 2, "low": 1}


def _health_score(alerts: list[dict], capacity: dict) -> float | None:
    """
    None quand la VM est injoignable : afficher 100/100 sans avoir rien pu
    mesurer donnerait une fausse assurance.
    """
    if capacity["unavailable"]:
        return None

    penalty = sum(_ALERT_WEIGHTS.get(alert.get("severity"), 1) for alert in alerts)
    if capacity["percent_used"] >= CAPACITY_CRITICAL_PERCENT:
        penalty += 8
    elif capacity["percent_used"] >= CAPACITY_WARNING_PERCENT:
        penalty += 3
    return round(max(100 - penalty, 0), 1)


def _headline(status: str, incidents: dict, backups: dict, capacity: dict) -> str:
    """Phrase courte en langage naturel, pas un code d'état."""
    if capacity["unavailable"]:
        return "I can't reach your storage VM right now"
    if incidents["by_severity"]["critical"]:
        count = incidents["by_severity"]["critical"]
        return f"{count} critical incident{'s' if count > 1 else ''} need your attention"
    if backups["failed"]:
        count = backups["failed"]
        return f"{count} backup job{'s' if count > 1 else ''} need your attention"
    if capacity["volumes_near_limit"]:
        count = capacity["volumes_near_limit"]
        return f"{count} volume{'s are' if count > 1 else ' is'} getting close to its capacity limit"
    if not backups["configured"]:
        return "Your volumes look fine, but nothing is backing them up yet"
    if status == "warning":
        return "A few things are worth a look, nothing urgent"
    return "Your storage environment is healthy"


def refresh_health_snapshot() -> tuple[datetime, dict]:
    """
    Interroge la VM et remplace le relevé en cache.

    Le verrou sérialise les rafraîchissements : sans lui, dix onglets ouverts
    en même temps sur un cache vide déclencheraient dix sessions SSH pour la
    même donnée. Celui qui obtient le verrou après un autre trouve le relevé
    déjà frais et repart sans rien demander à la VM.
    """
    global _health_cache

    with _refresh_lock:
        snapshot = _health_cache
        if snapshot is not None and time.monotonic() - snapshot[0] < _HEALTH_FRESH_SECONDS:
            return snapshot[1], snapshot[2]

        health = get_storage_health()
        checked_at = datetime.now(timezone.utc)
        with _health_lock:
            _health_cache = (time.monotonic(), checked_at, health)
        return checked_at, health


def _storage_health(force: bool = False) -> tuple[datetime, dict]:
    """Le dernier relevé connu ; la VM n'est interrogée que si besoin."""
    if force:
        _invalidate_health_snapshot()
        return refresh_health_snapshot()

    with _health_lock:
        snapshot = _health_cache

    if snapshot is None:
        return refresh_health_snapshot()

    if time.monotonic() - snapshot[0] >= _HEALTH_FRESH_SECONDS and not _refresh_lock.locked():
        # Périmé : on rend quand même la main tout de suite, le relevé suivant
        # servira l'affichage d'après.
        threading.Thread(
            target=_refresh_in_background, name="storage-health-refresh", daemon=True
        ).start()

    return snapshot[1], snapshot[2]


def _refresh_in_background() -> None:
    try:
        refresh_health_snapshot()
    except Exception:  # noqa: BLE001 -- la VM peut être injoignable
        logger.exception("Echec du rafraichissement du releve de sante Storage")


def _invalidate_health_snapshot() -> None:
    global _health_cache
    with _health_lock:
        _health_cache = None


def get_overview(db: Session, force_refresh: bool = False) -> dict:
    checked_at, health = _storage_health(force=force_refresh)
    capacity = _build_capacity(health.get("capacity", {}))
    backups = _build_backups(health.get("backups", {}))
    incidents = _build_incidents(db)
    alerts = health.get("alerts", [])

    status = health.get("overall_status", "healthy")
    if incidents["by_severity"]["critical"]:
        status = "critical"

    return {
        "overall_status": status,
        "headline": _headline(status, incidents, backups, capacity),
        "health_score": _health_score(alerts, capacity),
        "capacity": capacity,
        "backups": backups,
        "incidents": incidents,
        "alerts": alerts,
        "generated_at": datetime.now(timezone.utc),
        # Date du relevé sur la VM, distincte de celle de la réponse : elle dit
        # à l'interface quel âge ont réellement capacité et sauvegardes.
        "checked_at": checked_at,
    }


# --------------------------------------------------------------------------
# Performance
# --------------------------------------------------------------------------

def get_performance(db: Session, range_key: str = "24h") -> dict:
    """
    Série IOPS / débit / latence, relue depuis les échantillons réels prélevés
    sur la VM par le collecteur (app/services/metrics_service.py).

    Aucune génération : tant que le collecteur n'a rien enregistré, `points`
    est vide et le frontend explique qu'il attend les premières mesures.
    """
    series = metrics_service.read_series(db, range_key)
    return {**series, "collecting": not series["points"]}


# --------------------------------------------------------------------------
# Activité récente
# --------------------------------------------------------------------------

def get_recent_activity(db: Session, limit: int = 8) -> list[dict]:
    """Fusionne incidents et demandes d'action en un flux chronologique."""
    items = []

    tickets = (
        db.query(IncidentTicket)
        .order_by(IncidentTicket.created_at.desc())
        .limit(limit)
        .all()
    )
    for ticket in tickets:
        items.append({
            "id": str(ticket.id),
            "kind": "incident",
            "title": ticket.title,
            "resource": ticket.affected_system,
            "status": ticket.status.value,
            "severity": ticket.severity.value,
            "timestamp": ticket.created_at,
        })

    actions = (
        db.query(ActionRequest)
        .order_by(ActionRequest.created_at.desc())
        .limit(limit)
        .all()
    )
    for action in actions:
        items.append({
            "id": str(action.id),
            "kind": "action",
            "title": action.action_type.replace("_", " ").capitalize(),
            "resource": action.target,
            "status": action.status.value,
            "severity": None,
            "timestamp": action.created_at,
        })

    items.sort(key=lambda item: item["timestamp"], reverse=True)
    return items[:limit]


# --------------------------------------------------------------------------
# OASIS Insights
# --------------------------------------------------------------------------

def get_insights(db: Session) -> list[dict]:
    """
    Observations formulées en langage naturel, dérivées des mêmes seuils que
    le reste du dashboard. Chaque insight pointe vers l'écran qui permet d'agir.
    """
    overview = get_overview(db)
    insights: list[dict] = []

    if overview["capacity"]["unavailable"]:
        insights.append({
            "id": "vm-unreachable",
            "priority": "high",
            "title": "I can't reach your storage VM",
            "detail": (
                f"{overview['capacity']['error']} Until it answers, capacity, backups and "
                "performance on this page are unknown rather than healthy."
            ),
            "action_label": None,
            "action_target": None,
        })
        return insights

    for volume in overview["capacity"]["volumes"]:
        if volume["status"] == "healthy":
            continue
        insights.append({
            "id": f"capacity-{volume['volume_id']}",
            "priority": "critical" if volume["status"] == "critical" else "high",
            "title": f"{volume['mountpoint']} is approaching its capacity threshold",
            "detail": (
                f"{volume['percent_used']}% used, {volume['available_gb']} GB still available. "
                "Requesting more capacity now avoids a write failure later."
            ),
            "action_label": "Request capacity",
            "action_target": "/storage/requests/new",
        })

    if not overview["backups"]["configured"] and not overview["backups"]["error"]:
        insights.append({
            "id": "backups-missing",
            "priority": "high",
            "title": "Nothing is backing up your volumes yet",
            "detail": (
                "No backup timer is defined on the VM, so there is currently no restore point. "
                "Any systemd timer whose name contains \"backup\" will show up here automatically."
            ),
            "action_label": "Ask OASIS how to set one up",
            "action_target": "/storage/chat",
        })

    failed_jobs = [job for job in overview["backups"]["jobs"] if job["status"] == "failed"]
    if failed_jobs:
        targets = ", ".join(job["target"] for job in failed_jobs)
        insights.append({
            "id": "backups-failed",
            "priority": "high",
            "title": f"{len(failed_jobs)} backup job{'s have' if len(failed_jobs) > 1 else ' has'} failed",
            "detail": f"Affected targets: {targets}. Ask OASIS to look into the job logs.",
            "action_label": "Investigate with OASIS",
            "action_target": "/storage/chat",
        })

    # Le retard se mesure contre la cadence du timer, pas contre une durée
    # fixe : un job hebdomadaire vieux de quatre jours est à l'heure. Le seuil
    # vient de health.py, pour que l'insight et l'alerte disent la même chose.
    stale_jobs = [
        job
        for job in overview["backups"]["jobs"]
        if job["hours_since_last_success"] >= stale_after_hours(job)
    ]
    if stale_jobs:
        # Le plus en retard *par rapport à sa propre cadence* : un job
        # quotidien oublié depuis trois jours passe avant un hebdomadaire de
        # huit jours, même si celui-ci affiche plus d'heures.
        latest = max(
            stale_jobs,
            key=lambda job: job["hours_since_last_success"] / stale_after_hours(job),
        )
        cadence = describe_interval(latest["expected_interval_hours"])
        insights.append({
            "id": "backups-stale",
            "priority": "medium",
            "title": f"{len(stale_jobs)} backup job{'s are' if len(stale_jobs) > 1 else ' is'} overdue",
            "detail": (
                f"{latest['job_id']} is supposed to run {cadence}, but its last success "
                f"was {latest['hours_since_last_success']} hours ago."
            ),
            "action_label": "View backup health",
            "action_target": "/storage/dashboard",
        })

    critical = overview["incidents"]["by_severity"]["critical"]
    if critical:
        insights.append({
            "id": "incidents-critical",
            "priority": "critical",
            "title": f"{critical} critical incident{'s are' if critical > 1 else ' is'} still open",
            "detail": "These were raised automatically by OASIS and nobody has resolved them yet.",
            "action_label": "View incidents",
            "action_target": "/storage/incidents",
        })

    if not insights:
        insights.append({
            "id": "all-clear",
            "priority": "info",
            "title": "Nothing needs your attention right now",
            "detail": (
                "Capacity, backups and replication are all within their thresholds. "
                "OASIS will flag anything that changes."
            ),
            "action_label": None,
            "action_target": None,
        })

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    insights.sort(key=lambda insight: order.get(insight["priority"], 5))
    return insights
