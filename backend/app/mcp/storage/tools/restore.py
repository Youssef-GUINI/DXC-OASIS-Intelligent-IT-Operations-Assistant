"""
app/mcp/storage/tools/restore.py

Restauration réelle d'un volume à partir d'un snapshot LVM (`lvconvert --merge`),
via SSH.

Action destructive : elle écrase l'état courant du volume par celui du snapshot.
Conformément à STORAGE_SYSTEM_PROMPT, elle exige `confirm=True`. Sans
confirmation, on renvoie une demande de confirmation sans rien exécuter — c'est
le bouton « Confirmer » du frontend, via /storage/actions/{id}/confirm, qui est
le seul chemin menant à `confirm=True`.
"""

from __future__ import annotations

from app.mcp.storage.ssh import StorageVMError, quote, run


def restore_from_backup(target: str, backup_id: str, confirm: bool = False) -> dict:
    """
    `backup_id` est le nom du snapshot LVM à fusionner dans `target`.
    La fusion ne prend effet qu'au prochain démontage/remontage du volume :
    LVM la planifie et la termine à ce moment-là.
    """
    if not confirm:
        return {
            "action": "restore_requires_confirmation",
            "target": target,
            "backup_id": backup_id,
            "warning": (
                f"Fusionner le snapshot '{backup_id}' dans '{target}' écrasera les données "
                "actuelles du volume et supprimera le snapshot. Confirmation explicite requise."
            ),
        }

    try:
        output = run(f"sudo lvconvert --merge {quote(backup_id)}")
    except StorageVMError as error:
        return {
            "action": "restore_failed",
            "target": target,
            "backup_id": backup_id,
            "error": str(error),
        }

    return {
        "action": "restore_started",
        "target": target,
        "backup_id": backup_id,
        "status": "merging",
        "detail": output.strip() or "LVM scheduled the merge.",
        "note": (
            "LVM completes the merge the next time the volume is unmounted and remounted. "
            "Check with `lvs` that the snapshot is gone."
        ),
    }
