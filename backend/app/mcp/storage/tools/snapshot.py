"""
Tool MCP : snapshots. Données SIMULÉES pour la V1.
"""
from datetime import datetime, timedelta, timezone

_SIMULATED_SNAPSHOTS = {
    "vol-prod-db01": ["snap-db01-0801", "snap-db01-0802", "snap-db01-0803"],
    "vol-app-storage": ["snap-app-0801"],
}


def list_snapshots(volume_id: str) -> dict:
    """Liste les snapshots existants pour un volume."""
    snapshots = _SIMULATED_SNAPSHOTS.get(volume_id)
    if snapshots is None:
        return {"error": f"Volume '{volume_id}' introuvable ou sans snapshot connu"}

    now = datetime.now(timezone.utc)
    return {
        "volume_id": volume_id,
        "snapshots": [
            {
                "snapshot_id": snap_id,
                "created_at": (now - timedelta(days=i)).isoformat(),
            }
            for i, snap_id in enumerate(reversed(snapshots))
        ],
    }


def create_snapshot(volume_id: str) -> dict:
    """
    Crée un nouveau snapshot d'un volume.
    Action non destructive, pas de confirmation requise.
    """
    return {
        "action": "snapshot_created",
        "volume_id": volume_id,
        "snapshot_id": f"snap-{volume_id}-manual",
        "status": "completed",
    }