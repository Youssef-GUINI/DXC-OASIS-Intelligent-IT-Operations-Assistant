from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.mcp.linux.client import linux_mcp_client
from app.monitoring.thresholds import THRESHOLDS
from app.models.incident import Incident
from app.services.incident_service import auto_resolve_by_category
from app.personas.linux.agent import linux_persona

# Fenetre de temps et seuil utilises pour detecter une recurrence.
RECURRENCE_WINDOW_HOURS = 24
RECURRENCE_THRESHOLD = 3


def _severity_from_headroom(value: float, threshold: float, max_value: float = 100.0) -> str:
    """
    Classification dynamique de la severite en fonction de la position de la
    valeur mesuree dans la marge restante entre le seuil et le maximum
    theorique (100% pour cpu/ram/disk).

    Pourquoi pas un simple ratio valeur/seuil : pour des seuils eleves comme
    90%, le ratio ne peut jamais depasser 100/90 = 1.11, ce qui rend un
    palier "critical" fixe a 1.30 mathematiquement inatteignable. On mesure
    donc a la place la progression dans la marge [seuil -> max] :

      progress = (valeur - seuil) / (max - seuil)
        progress >= 0.7  -> critical (tres proche de la saturation)
        progress >= 0.3  -> high
        sinon            -> medium  (vient de depasser le seuil)
    """
    headroom = max_value - threshold
    if headroom <= 0:
        return "critical"
    progress = (value - threshold) / headroom
    if progress >= 0.7:
        return "critical"
    if progress >= 0.3:
        return "high"
    return "medium"


def _compute_recurrence_count(db: Session, persona: str, category: str) -> int:
    """
    Compte les incidents systeme de la meme categorie survenus dans les
    RECURRENCE_WINDOW_HOURS dernieres heures, +1 pour celui qu'on est en
    train de creer. Un compteur >= RECURRENCE_THRESHOLD signale un
    probleme qui revient sans cesse plutot qu'un incident isole.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=RECURRENCE_WINDOW_HOURS)
    recent_count = (
        db.query(Incident)
        .filter(
            Incident.persona == persona,
            Incident.category == category,
            Incident.source == "system",
            Incident.created_at >= cutoff,
        )
        .count()
    )
    return recent_count + 1


def detect_linux_incidents(db: Session) -> list[Incident]:
    created = []

    cpu = linux_mcp_client.call("get_cpu_usage")
    cpu_threshold = THRESHOLDS["cpu_usage_percent"]
    if cpu["usage_percent"] > cpu_threshold:
        created.append(_create_auto_incident(
            db, _severity_from_headroom(cpu["usage_percent"], cpu_threshold), "cpu",
            f"CPU a {cpu['usage_percent']}% (processus principal: {cpu['top_process']})",
        ))
    else:
        auto_resolve_by_category(db, "linux_persona", "cpu")

    ram = linux_mcp_client.call("get_ram_usage")
    ram_threshold = THRESHOLDS["ram_usage_percent"]
    if ram["usage_percent"] > ram_threshold:
        created.append(_create_auto_incident(
            db, _severity_from_headroom(ram["usage_percent"], ram_threshold), "ram",
            f"RAM a {ram['usage_percent']}% ({ram['used_gb']}/{ram['total_gb']} Go)",
        ))
    else:
        auto_resolve_by_category(db, "linux_persona", "ram")

    disk = linux_mcp_client.call("get_disk_usage")
    disk_threshold = THRESHOLDS["disk_usage_percent"]
    if disk["usage_percent"] > disk_threshold:
        created.append(_create_auto_incident(
            db, _severity_from_headroom(disk["usage_percent"], disk_threshold), "disk",
            f"Disque a {disk['usage_percent']}% sur {disk['mount_point']}",
        ))
    else:
        auto_resolve_by_category(db, "linux_persona", "disk")

    services = linux_mcp_client.call("get_services_status")
    failed = [name for name, status in services.items() if status == "failed"]
    if failed:
        # Severite basee sur le nombre de services en echec plutot qu'une
        # valeur fixe : un seul service isole est moins critique que
        # plusieurs services en panne simultanement.
        if len(failed) >= 3:
            services_severity = "critical"
        elif len(failed) == 2:
            services_severity = "high"
        else:
            services_severity = "medium"
        created.append(_create_auto_incident(
            db, services_severity, "services",
            f"Service(s) en echec : {', '.join(failed)}",
        ))
    else:
        auto_resolve_by_category(db, "linux_persona", "services")

    network = linux_mcp_client.call("check_network")
    network_threshold = THRESHOLDS["network_packet_loss_percent"]
    if network["packet_loss_percent"] > network_threshold:
        created.append(_create_auto_incident(
            db, _severity_from_headroom(network["packet_loss_percent"], network_threshold), "network",
            f"Perte de paquets reseau a {network['packet_loss_percent']}%",
        ))
    else:
        auto_resolve_by_category(db, "linux_persona", "network")

    return created


def _create_auto_incident(db: Session, severity: str, category: str, description: str) -> Incident:
    recurrence_count = _compute_recurrence_count(db, "linux_persona", category)

    incident = Incident(
        user_id=None,
        persona="linux_persona",
        source="system",
        status="open",
        severity=severity,
        category=category,
        user_message="[Detection automatique]",
        response=description,
        recurrence_count=recurrence_count,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    try:
        if recurrence_count >= RECURRENCE_THRESHOLD:
            diagnosis_prompt = (
                f"Un systeme de monitoring automatique a detecte l'anomalie suivante : "
                f"{description}. C'est la {recurrence_count}e fois que ce type d'incident "
                f"('{category}') survient dans les dernieres {RECURRENCE_WINDOW_HOURS}h : "
                f"il s'agit probablement d'un probleme recurrent plutot que d'un incident "
                f"isole. Analyse cette situation en te concentrant sur la cause racine "
                f"probable de cette recurrence (plutot qu'un simple correctif ponctuel), "
                f"et propose des etapes concretes pour resoudre le probleme durablement."
            )
        else:
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