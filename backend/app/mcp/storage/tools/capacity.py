"""
app/mcp/storage/tools/capacity.py

Lit la capacité réelle des volumes de la VM Storage via `df`, par SSH.
Aucune donnée simulée : si la VM ne répond pas, on renvoie l'erreur.
"""

from __future__ import annotations

from app.mcp.storage.ssh import StorageVMError, run

# Systèmes de fichiers "virtuels" que `df` remonte mais qui ne sont pas des
# volumes de stockage.
_IGNORED_FILESYSTEMS = ("tmpfs", "devtmpfs", "overlay", "proc", "sysfs", "cgroup", "squashfs")


def _parse_df(output: str) -> list[dict]:
    """
    Parse la sortie de `df -T -B1 -P`.
    -T : type de système de fichiers
    -B1 : tailles en octets, pas d'arrondi ambigu
    -P : format POSIX stable, une ligne par volume
    """
    volumes: list[dict] = []

    for line in output.strip().splitlines()[1:]:  # ignore l'en-tête
        parts = line.split()
        if len(parts) < 7:
            continue

        device, filesystem, total_b, used_b, available_b, percent, mountpoint = parts[:7]

        if filesystem in _IGNORED_FILESYSTEMS or not device.startswith("/dev/"):
            continue

        try:
            total_gb = round(int(total_b) / (1024**3), 1)
            used_gb = round(int(used_b) / (1024**3), 1)
            available_gb = round(int(available_b) / (1024**3), 1)
            percent_used = int(percent.rstrip("%"))
        except ValueError:
            continue

        volume_id = mountpoint.strip("/").replace("/", "-") or device.replace("/dev/", "")

        volumes.append({
            "volume_id": volume_id,
            "mountpoint": mountpoint,
            "device": device,
            "filesystem": filesystem,
            "total_gb": total_gb,
            "used_gb": used_gb,
            "available_gb": available_gb,
            "percent_used": percent_used,
        })

    return volumes


def get_capacity(volume_id: str | None = None) -> dict:
    """
    Retourne tous les volumes réels de la VM, ou celui qui correspond à
    `volume_id` (matché sur l'identifiant, le point de montage ou le device).
    """
    try:
        volumes = _parse_df(run("df -T -B1 -P"))
    except StorageVMError as error:
        return {"error": str(error), "volumes": []}

    if volume_id is None:
        return {"volumes": volumes}

    match = next(
        (v for v in volumes if volume_id in (v["volume_id"], v["mountpoint"], v["device"])),
        None,
    )
    if match is None:
        return {"error": f"No volume matching '{volume_id}' on the VM", "volumes": []}

    return {"volumes": [match]}
