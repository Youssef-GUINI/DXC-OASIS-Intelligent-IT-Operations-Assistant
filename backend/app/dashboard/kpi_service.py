from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.incident import Incident


def get_linux_kpis(db: Session) -> dict:
    base_query = db.query(Incident).filter(Incident.persona == "linux_persona")

    total = base_query.count()
    open_count = base_query.filter(Incident.status == "open").count()
    resolved_count = base_query.filter(Incident.status == "resolved").count()

    avg_resolution_seconds = (
        db.query(
            func.avg(
                func.extract("epoch", Incident.resolved_at - Incident.created_at)
            )
        )
        .filter(Incident.persona == "linux_persona", Incident.status == "resolved")
        .scalar()
    )
    avg_resolution_minutes = round(avg_resolution_seconds / 60, 1) if avg_resolution_seconds else None

    by_category = dict(
        db.query(Incident.category, func.count(Incident.id))
        .filter(Incident.persona == "linux_persona", Incident.category.isnot(None))
        .group_by(Incident.category)
        .all()
    )

    by_severity = dict(
        db.query(Incident.severity, func.count(Incident.id))
        .filter(Incident.persona == "linux_persona", Incident.severity.isnot(None))
        .group_by(Incident.severity)
        .all()
    )

    by_source = dict(
        db.query(Incident.source, func.count(Incident.id))
        .filter(Incident.persona == "linux_persona")
        .group_by(Incident.source)
        .all()
    )

    return {
        "total_incidents": total,
        "open_incidents": open_count,
        "resolved_incidents": resolved_count,
        "avg_resolution_minutes": avg_resolution_minutes,
        "incidents_by_category": by_category,
        "incidents_by_severity": by_severity,
        "incidents_by_source": by_source,
    }