from sqlalchemy.orm import Session

from app.models.user import User
from app.core.security import verify_password, create_access_token


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def login(db: Session, email: str, password: str) -> str | None:
    user = authenticate_user(db, email, password)
    if not user:
        return None
    return create_access_token(subject=user.email, role=user.role.name)