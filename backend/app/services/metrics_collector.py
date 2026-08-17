"""
app/services/metrics_collector.py

Tâche de fond qui prélève régulièrement les compteurs d'E/S de la VM Storage
et les enregistre, afin que le graphique Storage Performance ait un historique
réel à afficher.

Le prélèvement est bloquant (SSH + attente de deux lectures de
/proc/diskstats) : il tourne donc dans un thread, jamais sur la boucle
d'événements.
"""

from __future__ import annotations

import asyncio
import logging

from app.database.session import SessionLocal
from app.services import metrics_service

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 300
PURGE_EVERY_N_CYCLES = 288  # ~une fois par jour à 5 minutes d'intervalle


def _collect() -> dict:
    db = SessionLocal()
    try:
        return metrics_service.collect_once(db)
    finally:
        db.close()


def _purge() -> int:
    db = SessionLocal()
    try:
        return metrics_service.purge_old(db)
    finally:
        db.close()


async def run_forever() -> None:
    cycle = 0
    while True:
        try:
            report = await asyncio.to_thread(_collect)
            if report.get("error"):
                # VM éteinte ou injoignable : c'est une situation normale en
                # développement, on la journalise sans arrêter la boucle.
                logger.info("Collecte de métriques ignorée : %s", report["error"])
            else:
                logger.debug("Métriques enregistrées pour %s", report.get("devices"))

            cycle += 1
            if cycle % PURGE_EVERY_N_CYCLES == 0:
                deleted = await asyncio.to_thread(_purge)
                logger.info("Purge des métriques : %s lignes supprimées", deleted)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 -- la boucle doit survivre à tout
            logger.exception("Erreur inattendue dans le collecteur de métriques")

        await asyncio.sleep(INTERVAL_SECONDS)
