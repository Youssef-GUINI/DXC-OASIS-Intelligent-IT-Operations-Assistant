"""
app/services/incident_watcher.py

Tâche de fond qui surveille les jobs de sauvegarde et ouvre un ticket
d'incident quand l'un d'eux échoue.

Sans elle, un échec de sauvegarde n'apparaît nulle part dans les incidents :
les tickets ne sont créés que par le persona Storage, pendant une conversation
(cf. app/personas/storage/agent.py). Un job qui échoue la nuit ne produit donc
un ticket que si quelqu'un pense à interroger l'agent le lendemain. Les alertes
du dashboard, elles, sont recalculées à chaque appel et ne laissent aucune
trace.

La règle de détection n'est pas réécrite ici : c'est la même que celle du
persona (`check_backup_status`), pour que les deux chemins produisent des
tickets identiques.

La lecture des jobs est bloquante (SSH vers la VM) : elle tourne dans un
thread, jamais sur la boucle d'événements.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.incident_ticket import IncidentStatus, IncidentTicket
from app.models.role import Role
from app.models.user import User
from app.mcp.storage.tools.backup import list_backups
from app.personas.storage.incident_rules import check_backup_status
from app.services import incident_service

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 300

# `incident_tickets.created_by` est NOT NULL : un ticket ouvert par la
# surveillance doit être attribué à quelqu'un. Plutôt que de le mettre au
# compte d'un ingénieur qui n'a rien demandé, on utilise un compte de service
# dédié — l'audit distingue ainsi ce qu'OASIS a détecté seul de ce qu'un humain
# a demandé.
SYSTEM_ACCOUNT_EMAIL = "oasis-system@oasis.local"
SYSTEM_ACCOUNT_ROLE = "storage_engineer"

_CLOSED_STATUSES = (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)


def _system_user_id(db: Session) -> Optional[int]:
    """
    Renvoie l'identifiant du compte de service, en le créant au besoin.

    Le compte est `is_active=False` et porte un mot de passe aléatoire jamais
    communiqué : il ne peut pas servir à se connecter, `get_current_user`
    rejetant les comptes désactivés. Il n'existe que pour être l'auteur des
    tickets ouverts automatiquement.
    """
    user = db.execute(
        select(User).where(User.email == SYSTEM_ACCOUNT_EMAIL)
    ).scalars().first()
    if user is not None:
        return user.id

    role = db.execute(
        select(Role).where(Role.name == SYSTEM_ACCOUNT_ROLE)
    ).scalars().first()
    if role is None:
        logger.error(
            "Rôle %s absent : compte de service non créé, "
            "surveillance des sauvegardes inactive. Lancer le seed de la base.",
            SYSTEM_ACCOUNT_ROLE,
        )
        return None

    user = User(
        email=SYSTEM_ACCOUNT_EMAIL,
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        full_name="OASIS (surveillance automatique)",
        is_active=False,
        role_id=role.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Compte de service %s créé", SYSTEM_ACCOUNT_EMAIL)
    return user.id


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    """`last_run` est renvoyé en ISO 8601 par list_backups, ou None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _latest_ticket(db: Session, affected_system: str) -> Optional[IncidentTicket]:
    return db.execute(
        select(IncidentTicket)
        .where(IncidentTicket.affected_system == affected_system)
        .order_by(IncidentTicket.created_at.desc())
    ).scalars().first()


def _already_handled(ticket: Optional[IncidentTicket], last_run: Optional[datetime]) -> bool:
    """
    Vrai si cet échec a déjà donné lieu à un ticket que l'on a clos.

    Sans ce test, résoudre un ticket sur un job encore en échec en rouvrirait
    un identique au cycle suivant : le bouton « résoudre » n'aurait aucun
    effet visible. On ne rouvre donc qu'à partir d'une exécution postérieure
    au ticket précédent — un ticket par échec, et non par cycle.

    Les tickets encore ouverts ne sont pas concernés : create_ticket_from_diagnosis
    les met à jour au lieu d'en créer un second.
    """
    if ticket is None or ticket.status not in _CLOSED_STATUSES:
        return False
    if last_run is None:
        return True
    return ticket.created_at >= last_run


def scan_once() -> dict:
    """
    Un passage de surveillance. Renvoie un compte rendu, jamais d'exception :
    la VM éteinte est une situation normale, pas une panne de l'application.
    """
    backups = list_backups()
    if backups.get("error"):
        return {"error": backups["error"], "created": [], "skipped": []}

    failed = [job for job in backups.get("jobs", []) if job.get("status") == "failed"]
    if not failed:
        return {"created": [], "skipped": [], "checked": len(backups.get("jobs", []))}

    created: list[str] = []
    skipped: list[str] = []

    db = SessionLocal()
    try:
        author_id = _system_user_id(db)
        if author_id is None:
            return {"error": "compte de service indisponible", "created": [], "skipped": []}

        for job in failed:
            ticket_data = check_backup_status(job)
            if ticket_data is None:
                continue

            last_run = _parse_timestamp(job.get("last_run"))
            if _already_handled(_latest_ticket(db, ticket_data["affected_system"]), last_run):
                skipped.append(job.get("job_id", "?"))
                continue

            ticket = incident_service.create_ticket_from_diagnosis(
                db, created_by=author_id, **ticket_data,
            )
            created.append(ticket.ticket_number)
    finally:
        db.close()

    return {"created": created, "skipped": skipped, "checked": len(backups.get("jobs", []))}


async def run_forever() -> None:
    while True:
        try:
            report = await asyncio.to_thread(scan_once)
            if report.get("error"):
                # VM éteinte ou injoignable : normal en développement.
                logger.info("Surveillance des sauvegardes ignorée : %s", report["error"])
            elif report["created"]:
                logger.warning(
                    "Sauvegarde en échec détectée, ticket(s) ouvert(s) : %s",
                    ", ".join(report["created"]),
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Erreur pendant la surveillance des sauvegardes")

        await asyncio.sleep(INTERVAL_SECONDS)
