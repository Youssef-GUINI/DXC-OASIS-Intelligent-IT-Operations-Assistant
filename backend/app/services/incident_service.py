from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.incident import Incident


def save_incident(db: Session, user_id: int, persona: str, user_message: str, response: str) -> Incident:
    incident = Incident(
        user_id=user_id,
        persona=persona,
        source="user",
        status="open",
        user_message=user_message,
        response=response,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def list_incidents(db: Session, status: str | None = None, persona: str | None = None) -> list[Incident]:
    query = db.query(Incident)
    if status:
        query = query.filter(Incident.status == status)
    if persona:
        query = query.filter(Incident.persona == persona)
    return query.order_by(Incident.created_at.desc()).all()


def resolve_incident(db: Session, incident_id: int) -> Incident | None:
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        return None
    incident.status = "resolved"
    incident.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(incident)
    return incident


def auto_resolve_by_category(db: Session, persona: str, category: str) -> int:
    open_incidents = (
        db.query(Incident)
        .filter(
            Incident.persona == persona,
            Incident.category == category,
            Incident.source == "system",
            Incident.status == "open",
        )
        .all()
    )
    for incident in open_incidents:
        incident.status = "resolved"
        incident.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return len(open_incidents)


def get_recent_incidents_summary(db: Session, status: str | None = None, limit: int = 10) -> list[dict]:
    """
    Version simplifiee des incidents, pensee pour etre lue par le LLM
    (utilisee comme outil de tool-calling).
    """
    query = db.query(Incident).filter(Incident.persona == "linux_persona")
    if status:
        query = query.filter(Incident.status == status)
    incidents = query.order_by(Incident.created_at.desc()).limit(limit).all()

    return [
        {
            "id": i.id,
            "category": i.category or "n/a",
            "severity": i.severity or "n/a",
            "status": i.status,
            "description": i.response,
            "created_at": str(i.created_at),
        }
        for i in incidents
    ]