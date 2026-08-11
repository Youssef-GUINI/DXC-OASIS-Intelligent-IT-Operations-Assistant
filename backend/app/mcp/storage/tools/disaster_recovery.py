"""
Tool MCP : reprise après sinistre (DR). Données SIMULÉES pour la V1.
"""

_SIMULATED_DR_STATUS = {
    "primary_site": "DXC-DC-Paris",
    "dr_site": "DXC-DC-Lyon",
    "replication_status": "healthy",
    "replication_lag_seconds": 12,
    "last_failover_test": "2026-06-15",
}


def get_dr_status() -> dict:
    """Retourne l'état courant de la réplication DR."""
    return dict(_SIMULATED_DR_STATUS)


def initiate_failover(target_site: str, confirm: bool = False) -> dict:
    """
    Bascule le trafic vers le site de secours.
    Action fortement destructive/à impact majeur — confirmation
    explicite requise, même logique que restore_from_backup.
    """
    if not confirm:
        return {
            "action": "failover_requires_confirmation",
            "target_site": target_site,
            "warning": (
                f"Le basculement vers '{target_site}' interrompt temporairement le service "
                "et redirige tout le trafic depuis le site primaire. Confirmation explicite requise."
            ),
        }

    return {
        "action": "failover_completed",
        "target_site": target_site,
        "status": "success",
    }