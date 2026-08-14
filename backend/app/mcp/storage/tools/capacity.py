"""
app/mcp/storage/tools/capacity.py

RÉVISION (2026-08-12) : ce tool utilisait auparavant des données réelles
(psutil.disk_partitions / shutil.disk_usage sur la machine hébergeant le
backend). Décision initiale documentée dans JOURNAL_TECHNIQUE_SESSION.md
section 2.4.

Changement assumé : pour que l'analyse d'incident (analyze_incident) puisse
corréler capacité / backup / DR sur un même identifiant de volume, capacity
bascule sur des données SIMULÉES, avec les mêmes volume_id que ceux utilisés
dans _SIMULATED_JOBS (backup.py) et _SIMULATED_DR_STATUS (disaster_recovery.py).
Les volumes réels de la machine de dev/démo n'ont aucun rapport avec les
volumes fictifs du scénario d'incident (vol-prod-db01, etc.), donc les
mélanger produisait des résultats incohérents ("volume introuvable").

À documenter explicitement dans le rapport comme un choix assumé, daté,
et sa raison (cohérence de démo), pas comme une régression silencieuse.
"""

_SIMULATED_VOLUMES = {
    "vol-prod-db01": {
        "volume_id": "vol-prod-db01",
        "mountpoint": "/data/prod",
        "device": "/dev/sdb1",
        "filesystem": "ext4",
        "total_gb": 500,
        "used_gb": 465,
        "percent_used": 93,
    },
    "vol-nas01": {
        "volume_id": "vol-nas01",
        "mountpoint": "/data/nas",
        "device": "/dev/sdc1",
        "filesystem": "xfs",
        "total_gb": 2000,
        "used_gb": 1400,
        "percent_used": 70,
    },
    "vol-app01": {
        "volume_id": "vol-app01",
        "mountpoint": "/data/app",
        "device": "/dev/sdd1",
        "filesystem": "ext4",
        "total_gb": 200,
        "used_gb": 80,
        "percent_used": 40,
    },
}


def get_capacity(volume_id: str | None = None) -> dict:
    """
    Retourne un volume précis (matché par volume_id, mountpoint ou device),
    ou tous les volumes simulés si volume_id=None.
    """
    if volume_id is None:
        return {"volumes": list(_SIMULATED_VOLUMES.values())}

    volume = _SIMULATED_VOLUMES.get(volume_id)
    if volume is None:
        volume = next(
            (v for v in _SIMULATED_VOLUMES.values()
             if volume_id in (v["mountpoint"], v["device"])),
            None,
        )

    if volume is None:
        return {"error": f"Volume '{volume_id}' introuvable", "volumes": []}

    return {"volumes": [volume]}