"""
app/mcp/storage/tools/snapshot.py

Snapshots LVM réels de la VM Storage, lus et créés via SSH.

Aucune donnée simulée. Sur une VM sans LVM, `list_snapshots()` renvoie
`lvm_available: False` et une liste vide plutôt qu'une erreur : ne pas
utiliser LVM est une situation normale, pas une panne.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.mcp.storage.ssh import StorageVMError, quote, run

# Champs demandés à `lvs`, séparés par des espaces, sans en-tête.
_LVS_FIELDS = "lv_name,vg_name,origin,lv_size,data_percent,lv_time"
_LVS_COMMAND = f"lvs --noheadings --nosuffix --units g --separator '|' -o {_LVS_FIELDS}"


def _parse_lvs(output: str) -> list[dict]:
    volumes = []
    for line in output.strip().splitlines():
        parts = [part.strip() for part in line.strip().split("|")]
        if len(parts) < 6:
            continue
        name, group, origin, size, data_percent, created = parts[:6]
        volumes.append({
            "name": name,
            "volume_group": group,
            "origin": origin,
            "size_gb": float(size) if size else 0.0,
            "used_percent": float(data_percent) if data_percent else None,
            "created_at": created or None,
        })
    return volumes


def list_snapshots(volume_id: str | None = None) -> dict:
    """
    Liste les snapshots LVM. Un logical volume est un snapshot dès lors qu'il
    a une origine (`origin` non vide).
    """
    try:
        output = run(_LVS_COMMAND, allow_failure=True)
    except StorageVMError as error:
        return {"error": str(error), "snapshots": []}

    if not output.strip():
        return {"snapshots": [], "lvm_available": False}

    snapshots = [
        {
            "snapshot_id": volume["name"],
            "volume_id": volume["origin"],
            "volume_group": volume["volume_group"],
            "size_gb": volume["size_gb"],
            "used_percent": volume["used_percent"],
            "created_at": volume["created_at"],
        }
        for volume in _parse_lvs(output)
        if volume["origin"]
    ]

    if volume_id is not None:
        snapshots = [snap for snap in snapshots if snap["volume_id"] == volume_id]
        if not snapshots:
            return {
                "volume_id": volume_id,
                "snapshots": [],
                "lvm_available": True,
                "note": f"No LVM snapshot for '{volume_id}'",
            }

    return {"snapshots": snapshots, "lvm_available": True}


def create_snapshot(volume_id: str, volume_group: str | None = None, size_gb: float = 1.0) -> dict:
    """
    Crée un snapshot LVM du volume donné.
    Action non destructive : elle ajoute un volume, elle n'écrase rien.
    """
    if volume_group is None:
        try:
            origins = _parse_lvs(run(_LVS_COMMAND, allow_failure=True))
        except StorageVMError as error:
            return {"error": str(error)}

        match = next((volume for volume in origins if volume["name"] == volume_id), None)
        if match is None:
            return {"error": f"Logical volume '{volume_id}' not found on the VM"}
        volume_group = match["volume_group"]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snapshot_name = f"{volume_id}-snap-{stamp}"
    source = f"/dev/{volume_group}/{volume_id}"

    try:
        run(
            f"sudo lvcreate --snapshot --size {float(size_gb)}G "
            f"--name {quote(snapshot_name)} {quote(source)}"
        )
    except StorageVMError as error:
        return {"error": str(error), "action": "snapshot_failed", "volume_id": volume_id}

    return {
        "action": "snapshot_created",
        "volume_id": volume_id,
        "snapshot_id": snapshot_name,
        "volume_group": volume_group,
        "status": "completed",
    }
