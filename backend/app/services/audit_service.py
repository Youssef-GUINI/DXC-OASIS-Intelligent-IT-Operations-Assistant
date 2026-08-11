"""
Logique métier de consultation des audit logs. L'écriture des logs est
gérée automatiquement par app/middleware/audit_middleware.py — ce
service ne fait que la LECTURE, pour l'Admin Workspace.
"""
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def list_recent(db: Session, limit: int = 50) -> list[AuditLog]:
    return (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )