from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import create_cross_domain_token
from app.models.access_request import AccessRequest, AccessRequestStatus
from app.models.user import User
from app.schemas.access_request import AccessRequestCreate


def create_request(db: Session, user: User, request_in: AccessRequestCreate) -> AccessRequest:
    new_request = AccessRequest(
        requested_by_id=user.id,
        target_workspace=request_in.target_workspace,
        reason=request_in.reason,
        status=AccessRequestStatus.PENDING,
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request


def list_pending(db: Session) -> list[AccessRequest]:
    return (
        db.query(AccessRequest)
        .filter(AccessRequest.status == AccessRequestStatus.PENDING)
        .order_by(AccessRequest.created_at.asc())
        .all()
    )


def approve_request(db: Session, request_id: int, admin: User, token_minutes: int = 30) -> AccessRequest | None:
    access_request = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if access_request is None:
        return None

    token = create_cross_domain_token(
        subject=access_request.requested_by.email,
        workspace=access_request.target_workspace,
        minutes=token_minutes,
    )

    access_request.status = AccessRequestStatus.APPROVED
    access_request.reviewed_by_id = admin.id
    access_request.granted_token = token
    access_request.expires_at = datetime.now(timezone.utc) + timedelta(minutes=token_minutes)
    access_request.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(access_request)
    return access_request


def reject_request(db: Session, request_id: int, admin: User) -> AccessRequest | None:
    access_request = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if access_request is None:
        return None

    access_request.status = AccessRequestStatus.REJECTED
    access_request.reviewed_by_id = admin.id
    access_request.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(access_request)
    return access_request