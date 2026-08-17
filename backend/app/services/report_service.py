from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.report import Report
from app.reports.generator import generate_incident_report
from app.dashboard.kpi_service import get_linux_kpis


def create_report_for_incident(db: Session, incident_id: int, user_id: int) -> Report | None:
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        return None

    kpis = get_linux_kpis(db)
    filepath = generate_incident_report(incident, kpis=kpis)

    report = Report(
        incident_id=incident.id,
        generated_by=user_id,
        file_path=filepath,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
from app.reports.generator import generate_global_report
from app.services.incident_service import list_incidents


def create_global_report(db: Session, user_id: int) -> Report:
    kpis = get_linux_kpis(db)
    open_incidents = list_incidents(db, status="open", persona="linux_persona")
    resolved_incidents = list_incidents(db, status="resolved", persona="linux_persona")

    filepath = generate_global_report(kpis, open_incidents, resolved_incidents)

    report = Report(
        incident_id=None,
        generated_by=user_id,
        file_path=filepath,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report