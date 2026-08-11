"""
Tool MCP : restauration. Données SIMULÉES pour la V1.

Action potentiellement destructive (écrase les données actuelles du
volume cible) — conformément à STORAGE_SYSTEM_PROMPT, elle exige un
paramètre confirm=True explicite. Sans confirmation, on renvoie une
demande de confirmation plutôt que d'exécuter, pour que le Persona
relaie cette exigence à l'utilisateur au lieu d'agir directement.
"""


def restore_from_backup(target: str, backup_id: str, confirm: bool = False) -> dict:
    if not confirm:
        return {
            "action": "restore_requires_confirmation",
            "target": target,
            "backup_id": backup_id,
            "warning": (
                f"La restauration de '{backup_id}' sur '{target}' écrasera les données "
                "actuelles du volume cible. Confirmation explicite requise avant exécution."
            ),
        }

    return {
        "action": "restore_completed",
        "target": target,
        "backup_id": backup_id,
        "status": "success",
    }