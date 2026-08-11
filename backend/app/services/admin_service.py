"""
Logique métier de l'Admin Workspace (lecture seule) : consultation des
comptes utilisateurs et des rôles.
"""
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.role import Role


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.id.asc()).all()


def list_roles(db: Session) -> list[Role]:
    return db.query(Role).order_by(Role.id.asc()).all()