from sqlalchemy.orm import Session

from app.mcp.linux.client import linux_mcp_client
from app.monitoring.thresholds import THRESHOLDS
from app.models.incident import Incident
from app.services.incident_service import auto_resolve_by_category
from app.personas.linux.agent import linux_persona


def detect_linux_incidents(db: Session) -> list[Incident]:
    created = []

    cpu = linux_mcp_client.call("get_cpu_usage")
    if cpu["usage_percent"] > THRESHOLDS["cpu_usage_percent"]:
        created.append(_create_auto_incident(
            db, "high", "cpu",
            f"CPU a {cpu['usage_percent']}% (processus principal: {cpu['top_process']})",
        ))
    else:
        auto_resolve_by_category(db, "linux_persona", "cpu")

    ram = linux_mcp_client.call("get_ram_usage")
    if ram["usage_percent"] > THRESHOLDS["ram_usage_percent"]:
        created.append(_create_auto_incident(
            db, "high", "ram",
            f"RAM a {ram['usage_percent']}% ({ram['used_gb']}/{ram['total_gb']} Go)",
        ))
    else:
        auto_resolve_by_category(db, "linux_persona", "ram")

    disk = linux_mcp_client.call("get_disk_usage")
    if disk["usage_percent"] > THRESHOLDS["disk_usage_percent"]:
        created.append(_create_auto_incident(
            db, "medium", "disk",
            f"Disque a {disk['usage_percent']}% sur {disk['mount_point']}",
        ))
    else:
        auto_resolve_by_category(db, "linux_persona", "disk")

    services = linux_mcp_client.call("get_services_status")
    failed = [name for name, status in services.items() if status == "failed"]
    if failed:
        created.append(_create_auto_incident(
            db, "high", "services",
            f"Service(s) en echec : {', '.join(failed)}",
        ))
    else:
        auto_resolve_by_category(db, "linux_persona", "services")

    network = linux_mcp_client.call("check_network")
    if network["packet_loss_percent"] > THRESHOLDS["network_packet_loss_percent"]:
        created.append(_create_auto_incident(
            db, "medium", "network",
            f"Perte de paquets reseau a {network['packet_loss_percent']}%",
        ))
    else:
        auto_resolve_by_category(db, "linux_persona", "network")

    return created


def _create_auto_incident(db: Session, severity: str, category: str, description: str) -> Incident:
    incident = Incident(
        user_id=None,
        persona="linux_persona",
        source="system",
        status="open",
        severity=severity,
        category=category,
        user_message="[Detection automatique]",
        response=description,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    try:
        diagnosis_prompt = (
            f"Un systeme de monitoring automatique a detecte l'anomalie suivante : "
            f"{description}. Analyse cette situation, explique la cause probable, "
            f"et propose des etapes concretes de resolution."
        )
        diagnosis = linux_persona.handle_message(diagnosis_prompt, db=db)
        incident.diagnosis = diagnosis
        db.commit()
    except Exception as exc:
        print(f"[monitoring] Erreur lors du diagnostic LLM : {exc}")

    return incident