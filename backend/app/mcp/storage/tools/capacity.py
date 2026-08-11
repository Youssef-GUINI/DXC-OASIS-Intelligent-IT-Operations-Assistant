"""
Tool MCP : capacité de stockage.

Données SIMULÉES pour la V1 — pas encore branché sur une vraie baie ou
un vrai cloud provider. La structure de retour (dict avec des clés
stables) est volontairement pensée pour rester identique le jour où on
branchera une vraie source (API NetApp, AWS EBS, etc.), afin que le
Persona et le prompt n'aient rien à changer.
"""

_SIMULATED_VOLUMES = {
    "vol-prod-db01": {"total_gb": 2000, "used_gb": 1840, "pool": "tier1-ssd"},
    "vol-backup-nas01": {"total_gb": 8000, "used_gb": 7120, "pool": "tier2-hdd"},
    "vol-app-storage": {"total_gb": 1000, "used_gb": 410, "pool": "tier1-ssd"},
}


def get_capacity(volume_id: str | None = None) -> dict:
    """
    Retourne l'état de capacité d'un volume précis, ou de tous les
    volumes connus si volume_id est omis.
    """
    if volume_id:
        volume = _SIMULATED_VOLUMES.get(volume_id)
        if volume is None:
            return {"error": f"Volume '{volume_id}' introuvable", "known_volumes": list(_SIMULATED_VOLUMES)}
        return {"volume_id": volume_id, **volume, "used_percent": round(volume["used_gb"] / volume["total_gb"] * 100, 1)}

    return {
        "volumes": [
            {"volume_id": vid, **v, "used_percent": round(v["used_gb"] / v["total_gb"] * 100, 1)}
            for vid, v in _SIMULATED_VOLUMES.items()
        ]
    }