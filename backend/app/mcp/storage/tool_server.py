"""
Storage MCP Server — implémentation avec le SDK officiel `mcp` (v2.0.0).

Ce fichier est un SCRIPT EXÉCUTABLE, pas juste un module importé : il est
lancé comme sous-process (`python -m app.mcp.storage.tool_server`) par le
client, et communique avec lui en JSON-RPC via stdin/stdout (transport
"stdio"). Ce découplage process est la vraie sémantique du protocole MCP
(contrairement à la V1 in-process qu'on avait commencée).

La logique métier de chaque tool reste dans app/mcp/storage/tools/*.py,
inchangée — ce fichier ne fait qu'exposer ces fonctions au protocole MCP
via le décorateur @server.tool().
"""
from mcp.server.mcpserver import MCPServer

from app.mcp.storage.tools import capacity, backup, snapshot, restore, disaster_recovery

server = MCPServer("oasis-storage-mcp")


@server.tool()
def get_capacity(volume_id: str | None = None) -> dict:
    """Retourne la capacité utilisée/totale d'un volume, ou de tous les volumes si volume_id est omis."""
    return capacity.get_capacity(volume_id)


@server.tool()
def list_backups(target: str | None = None) -> dict:
    """Liste les jobs de sauvegarde, éventuellement filtrés par volume cible."""
    return backup.list_backups(target)


@server.tool()
def run_backup(target: str) -> dict:
    """Déclenche une sauvegarde immédiate d'un volume."""
    return backup.run_backup(target)


@server.tool()
def list_snapshots(volume_id: str) -> dict:
    """Liste les snapshots existants d'un volume."""
    return snapshot.list_snapshots(volume_id)


@server.tool()
def create_snapshot(volume_id: str) -> dict:
    """Crée un nouveau snapshot d'un volume."""
    return snapshot.create_snapshot(volume_id)


@server.tool()
def restore_from_backup(target: str, backup_id: str, confirm: bool = False) -> dict:
    """Restaure un volume depuis une sauvegarde. Action destructive : exige confirm=True."""
    return restore.restore_from_backup(target, backup_id, confirm)


@server.tool()
def get_dr_status() -> dict:
    """Retourne l'état courant de la réplication disaster recovery."""
    return disaster_recovery.get_dr_status()


@server.tool()
def initiate_failover(target_site: str, confirm: bool = False) -> dict:
    """Bascule le trafic vers le site de secours. Action destructive : exige confirm=True."""
    return disaster_recovery.initiate_failover(target_site, confirm)


if __name__ == "__main__":
    # Point d'entrée du sous-process : boucle stdio bloquante tant que le
    # client (voir client.py) garde le process ouvert.
    server.run(transport="stdio")