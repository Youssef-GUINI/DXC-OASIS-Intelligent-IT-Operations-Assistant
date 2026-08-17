"""Registre unique des outils Storage et de leur niveau de risque."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.mcp.storage.tools.backup import (
    get_backup_job_status,
    get_backup_logs,
    list_backups,
    run_backup,
)
from app.mcp.storage.tools.capacity import get_capacity
from app.mcp.storage.tools.health import get_storage_health
from app.mcp.storage.tools.restore import restore_from_backup
from app.mcp.storage.tools.snapshot import create_snapshot, list_snapshots

TOOL_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "get_capacity": get_capacity,
    "list_backups": list_backups,
    "run_backup": run_backup,
    "get_backup_job_status": get_backup_job_status,
    "get_backup_logs": get_backup_logs,
    "list_snapshots": list_snapshots,
    "create_snapshot": create_snapshot,
    "get_storage_health": get_storage_health,
    "restore_from_backup": restore_from_backup,
}

# Applique par le persona et la route Actions; le serveur MCP reste neutre.
DESTRUCTIVE_TOOLS = frozenset({"restore_from_backup"})


def risk_for(tool_name: str) -> str:
    return "HIGH" if tool_name in DESTRUCTIVE_TOOLS else "LOW"


def invoke(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        return TOOL_REGISTRY[tool_name](**arguments)
    except KeyError as error:
        raise ValueError(f"Outil Storage inconnu : {tool_name}") from error
