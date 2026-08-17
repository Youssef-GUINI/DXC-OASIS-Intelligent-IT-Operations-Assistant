"""
app/mcp/storage/tools/performance.py

Lit les compteurs d'E/S disque réels de la VM Storage dans /proc/diskstats.

/proc/diskstats expose des compteurs cumulatifs depuis le démarrage : une
seule lecture ne dit rien. On lit donc deux fois, espacées de `SAMPLE_SECONDS`,
et on dérive les débits de la différence — exactement ce que fait `iostat`.

Aucune donnée simulée : sans VM joignable, on renvoie une erreur.
"""

from __future__ import annotations

import re

from app.mcp.storage.ssh import StorageVMError, run

SAMPLE_SECONDS = 2

# Secteur logique Linux : toujours 512 octets dans /proc/diskstats, quelle que
# soit la taille de secteur physique du disque.
_SECTOR_BYTES = 512

# Périphériques virtuels sans intérêt pour la performance de stockage.
_IGNORED_PREFIXES = ("loop", "ram", "sr", "fd")

# Partitions : leurs E/S sont déjà comptées dans le disque parent, les inclure
# reviendrait à compter deux fois. On garde sda, nvme0n1, dm-0 ; on écarte
# sda1, nvme0n1p2, vdb3.
_PARTITION = re.compile(r"^(?:[svh]d[a-z]+\d+|nvme\d+n\d+p\d+|mmcblk\d+p\d+)$")


def _parse_diskstats(output: str) -> dict[str, dict[str, int]]:
    """
    Champs de /proc/diskstats, en indices 0 (le fichier est documenté en
    numérotation 1) :
      [2]  nom du device
      [3]  lectures terminées   [5]  secteurs lus     [6]  ms passés en lecture
      [7]  écritures terminées  [9]  secteurs écrits  [10] ms passés en écriture
    """
    devices: dict[str, dict[str, int]] = {}

    for line in output.strip().splitlines():
        fields = line.split()
        if len(fields) < 14:
            continue

        name = fields[2]
        if name.startswith(_IGNORED_PREFIXES) or _PARTITION.match(name):
            continue

        try:
            devices[name] = {
                "reads": int(fields[3]),
                "read_sectors": int(fields[5]),
                "read_ms": int(fields[6]),
                "writes": int(fields[7]),
                "write_sectors": int(fields[9]),
                "write_ms": int(fields[10]),
            }
        except ValueError:
            continue

    return devices


def _rates(first: dict[str, int], second: dict[str, int], seconds: float) -> dict[str, float] | None:
    operations = (second["reads"] - first["reads"]) + (second["writes"] - first["writes"])
    sectors = (second["read_sectors"] - first["read_sectors"]) + (
        second["write_sectors"] - first["write_sectors"]
    )
    busy_ms = (second["read_ms"] - first["read_ms"]) + (second["write_ms"] - first["write_ms"])

    # Compteur remis à zéro (redémarrage entre les deux lectures) : échantillon
    # inexploitable, on préfère ne rien enregistrer plutôt qu'une valeur fausse.
    if operations < 0 or sectors < 0 or busy_ms < 0:
        return None

    return {
        "iops": round(operations / seconds, 2),
        "throughput_mbps": round(sectors * _SECTOR_BYTES / seconds / (1024**2), 2),
        # Temps d'attente moyen par opération sur l'intervalle.
        "latency_ms": round(busy_ms / operations, 2) if operations else 0.0,
    }


def sample_disk_performance() -> dict:
    """
    Prélève un échantillon de performance pour chaque device de la VM.

    Retourne {"devices": {nom: {iops, throughput_mbps, latency_ms}}} ou
    {"error": "..."} si la VM ne répond pas.
    """
    try:
        # Les deux lectures et l'attente se font sur la VM, en une seule session
        # SSH : ouvrir deux connexions coûterait plus que l'intervalle mesuré.
        output = run(
            f"cat /proc/diskstats; echo '---'; sleep {SAMPLE_SECONDS}; cat /proc/diskstats"
        )
    except StorageVMError as error:
        return {"error": str(error), "devices": {}}

    before_text, separator, after_text = output.partition("---")
    if not separator:
        return {"error": "Incomplete /proc/diskstats read on the VM", "devices": {}}

    before = _parse_diskstats(before_text)
    after = _parse_diskstats(after_text)

    devices = {}
    for name, first in before.items():
        second = after.get(name)
        if second is None:
            continue
        rates = _rates(first, second, SAMPLE_SECONDS)
        if rates is not None:
            devices[name] = rates

    if not devices:
        return {"error": "No usable device found in /proc/diskstats", "devices": {}}

    return {"devices": devices, "sample_seconds": SAMPLE_SECONDS}
