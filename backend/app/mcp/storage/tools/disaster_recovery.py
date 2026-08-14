"""
À REMPLACER dans app/mcp/storage/tools/disaster_recovery.py (fichier
existant) : la définition de _SIMULATED_DR_STATUS, clés alignées sur les
mêmes volume_id que capacity.py / backup.py.

Structure attendue par get_storage_health() (tools/health.py) :
un dict indexé par nom de cible, avec replication_lag_minutes et
rpo_target_minutes par entrée — adapter tools/health.py si la structure
réelle existante diffère (ex: liste au lieu de dict).
"""

_SIMULATED_DR_STATUS = {
    "vol-prod-db01": {
        "primary_site": "datacenter-A",
        "secondary_site": "datacenter-B",
        "replication_lag_minutes": 145,
        "rpo_target_minutes": 60,
        "last_failover_test": "2026-05-14",
    },
    "vol-nas01": {
        "primary_site": "datacenter-A",
        "secondary_site": "datacenter-B",
        "replication_lag_minutes": 12,
        "rpo_target_minutes": 60,
        "last_failover_test": "2026-05-14",
    },
    "vol-app01": {
        "primary_site": "datacenter-A",
        "secondary_site": "datacenter-B",
        "replication_lag_minutes": 8,
        "rpo_target_minutes": 60,
        "last_failover_test": "2026-05-14",
    },
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
"""
À AJOUTER à app/mcp/storage/tools/disaster_recovery.py (fichier existant).

get_dr_status() existant retourne déjà l'essentiel, mais analyze_incident a
besoin d'un tool dédié et plus ciblé sur le lag de réplication (RPO), pour
que le LLM puisse l'appeler indépendamment sans tirer tout le statut DR.
"""

# Réutilise _SIMULATED_DR_STATUS déjà défini dans disaster_recovery.py


def get_replication_status(target: str | None = None) -> dict:
    """
    Retourne le statut de réplication DR pour une cible donnée (ou toutes),
    avec le lag actuel comparé au RPO (Recovery Point Objective) attendu.
    """
    entries = _SIMULATED_DR_STATUS if target is None else {
        k: v for k, v in _SIMULATED_DR_STATUS.items() if k == target
    }

    result = []
    for name, status in entries.items():
        lag_minutes = status.get("replication_lag_minutes", 0)
        rpo_minutes = status.get("rpo_target_minutes", 60)
        result.append({
            "target": name,
            "replication_lag_minutes": lag_minutes,
            "rpo_target_minutes": rpo_minutes,
            "rpo_breached": lag_minutes > rpo_minutes,
            "last_failover_test": status.get("last_failover_test"),
        })
    return {"replication": result}