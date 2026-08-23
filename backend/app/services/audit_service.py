from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def list_recent(db: Session, limit: int = 50) -> list[AuditLog]:
    return (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )