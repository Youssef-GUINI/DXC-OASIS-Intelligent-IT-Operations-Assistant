"""
app/services/incident_verification.py

Dernière étape du cycle de vie d'un incident : vérifier sur la VM que la
remédiation confirmée a bien produit son effet, puis clore le ticket.

Un ticket ne se referme donc pas parce qu'une action s'est terminée sans
erreur, mais parce que la condition qui l'avait ouvert n'est plus vraie. La
distinction compte : `systemctl start` réussit à lancer un job qui échouera
trois secondes plus tard, et un ticket clos sur cette seule base mentirait.

La vérification réutilise les règles de détection (`incident_rules`) plutôt
que d'en réécrire une variante : ce qui a ouvert le ticket est exactement ce
qui doit avoir disparu pour le fermer.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from app.personas.storage.incident_rules import check_backup_status, check_capacity

logger = logging.getLogger(__name__)

# Un job systemd de type oneshot est encore `running` juste après un
# `systemctl start` : conclure tout de suite reviendrait à déclarer résolu un
# job dont on ne connaît pas encore l'issue. On lui laisse ce délai, et si
# cela ne suffit pas, la surveillance périodique reprendra la vérification
# au cycle suivant (cf. incident_watcher).
_RUNNING_POLL_ATTEMPTS = 5
_RUNNING_POLL_DELAY_SECONDS = 3


class Verdict:
    """Résultat d'une vérification, avec la phrase à écrire dans l'audit."""

    def __init__(self, resolved: bool, detail: str, conclusive: bool = True) -> None:
        self.resolved = resolved
        self.detail = detail
        # Non concluant : ni résolu ni toujours en panne -- l'état n'est pas
        # encore lisible (job en cours). Le ticket reste ouvert sans que cela
        # signifie un échec de la remédiation.
        self.conclusive = conclusive

    def __repr__(self) -> str:  # pragma: no cover -- confort de debug
        return f"<Verdict resolved={self.resolved} conclusive={self.conclusive}>"


def _job_from(result: dict[str, Any], job_id: str) -> Optional[dict]:
    for job in result.get("jobs", []) or []:
        if job.get("job_id") == job_id or job.get("target") == job_id:
            return job
    return None


async def _verify_backup(mcp, *, db, user_id: int, job_id: str) -> Verdict:
    job: Optional[dict] = None

    for attempt in range(_RUNNING_POLL_ATTEMPTS):
        result = await mcp.call_tool(
            "get_backup_job_status", db=db, user_id=user_id, target=job_id
        )
        job = _job_from(result, job_id)
        if job is None:
            return Verdict(
                False,
                f"Job {job_id} no longer exists on the VM: nothing to verify, "
                f"the ticket stays open for a human decision.",
            )
        if job.get("status") != "running":
            break
        if attempt < _RUNNING_POLL_ATTEMPTS - 1:
            await asyncio.sleep(_RUNNING_POLL_DELAY_SECONDS)

    if job is None:  # pragma: no cover -- la boucle tourne au moins une fois
        return Verdict(False, "Job status unreadable.", conclusive=False)

    status = job.get("status")
    if status == "running":
        return Verdict(
            False,
            f"Job {job_id} is still running: verification deferred to the next "
            f"monitoring pass.",
            conclusive=False,
        )

    if check_backup_status(job) is None:
        return Verdict(True, f"Verified on the VM: job {job_id} is now \"{status}\".")

    error_code = job.get("error_code") or "unknown"
    return Verdict(
        False,
        f"Job {job_id} is still failing (systemd result: {error_code}). "
        f"The ticket stays open.",
    )


async def _verify_capacity(mcp, *, db, user_id: int, volume_id: str) -> Verdict:
    result = await mcp.call_tool("get_capacity", db=db, user_id=user_id, volume_id=volume_id)
    volumes = result.get("volumes", []) or []
    if not volumes:
        return Verdict(
            False,
            f"Volume {volume_id} not found on the VM: the ticket stays open.",
        )

    volume = volumes[0]
    if check_capacity(volume) is None:
        return Verdict(
            True,
            f"Verified on the VM: {volume_id} is back down to "
            f"{volume.get('percent_used', '?')}% used.",
        )
    return Verdict(
        False,
        f"{volume_id} is still at {volume.get('percent_used', '?')}%: "
        f"the ticket stays open.",
    )


async def verify(ticket, *, mcp, db, user_id: int) -> Verdict:
    """
    Relit sur la VM l'indicateur qui avait ouvert le ticket.

    Le type d'incident se déduit de `mcp_data`, le relevé conservé au moment
    de la détection : c'est la seule information qui dise sur quoi porter la
    vérification, `affected_system` étant un libellé lisible (la Description
    systemd de l'unit) et non un identifiant interrogeable.
    """
    data = ticket.mcp_data or {}

    try:
        if data.get("job_id"):
            return await _verify_backup(mcp, db=db, user_id=user_id, job_id=data["job_id"])
        if data.get("volume_id") or data.get("mountpoint"):
            return await _verify_capacity(
                mcp, db=db, user_id=user_id,
                volume_id=data.get("volume_id") or data["mountpoint"],
            )
    except Exception as error:  # noqa: BLE001 -- VM injoignable, MCP tombé…
        logger.warning("Vérification de %s impossible : %s", ticket.ticket_number, error)
        return Verdict(False, f"Verification failed: {error}", conclusive=False)

    return Verdict(
        False,
        "No automatic verification exists for this kind of incident: "
        "closing it stays manual.",
        conclusive=False,
    )
