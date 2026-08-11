"""
Routes de l'Admin Workspace : consultation des comptes, des rôles et
des audit logs. Couche HTTP uniquement — la logique réelle vit dans
app/services/admin_service.py et app/services/audit_service.py.

Toutes les routes sont réservées au rôle "administrator".
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.user import UserResponse
from app.schemas.admin_schemas import RoleResponse, AuditLogResponse
from app.services import admin_service, audit_service

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_user_response(user: User) -> UserResponse:
    """UserResponse.role attend une chaîne, alors que User.role est une
    relation SQLAlchemy (objet Role) — construction manuelle nécessaire."""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name,
    )


# --- Consultation des comptes utilisateurs ---

@router.get("/users", response_model=list[UserResponse])
def list_users(
    current_user: User = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    users = admin_service.list_users(db)
    return [_to_user_response(u) for u in users]


# --- Consultation des rôles ---

@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    current_user: User = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    return admin_service.list_roles(db)


# --- Consultation des audit logs ---

@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    limit: int = 50,
    current_user: User = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    return audit_service.list_recent(db, limit=limit)