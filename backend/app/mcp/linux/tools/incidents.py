from app.database.session import SessionLocal
from app.models.incident import Incident


def get_incidents(
    status: str | None = None,
    severity: str | None = None,
    limit: int = 10,
):
    db = SessionLocal()

    try:
        query = (
            db.query(Incident)
            .filter(Incident.persona == "linux_persona")
        )

        if status:
            query = query.filter(Incident.status == status)

        if severity:
            query = query.filter(Incident.severity == severity)

        incidents = (
            query
            .order_by(Incident.created_at.desc())
            .limit(limit)
            .all()
        )

        return {
            "count": len(incidents),
            "incidents": [
                {
                    "id": incident.id,
                    "status": incident.status,
                    "severity": incident.severity,
                    "category": incident.category,
                    "source": incident.source,
                    "message": incident.user_message,
                    "diagnosis": incident.diagnosis,
                    "created_at": (
                        incident.created_at.isoformat()
                        if incident.created_at
                        else None
                    ),
                    "resolved_at": (
                        incident.resolved_at.isoformat()
                        if incident.resolved_at
                        else None
                    ),
                }
                for incident in incidents
            ],
        }

    finally:
        db.close()