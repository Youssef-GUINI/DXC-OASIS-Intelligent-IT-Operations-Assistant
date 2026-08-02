"""
Routes du workflow cross-domain. Couche HTTP uniquement — toute la
logique réelle vit dans app/services/access_request_service.py.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.schemas.access_request import (
    AccessRequestCreate,
    AccessRequestResponse,
    AccessRequestDecision,
)
from app.services import access_request_service

router = APIRouter(prefix="/cross-domain", tags=["cross-domain"])


@router.post("/requests", response_model=AccessRequestResponse, status_code=status.HTTP_201_CREATED)
def create_access_request(
    payload: AccessRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Étape 1 du workflow : n'importe quel utilisateur connecté peut
    demander un accès temporaire à un autre workspace.
    """
    return access_request_service.create_request(db, current_user, payload)


@router.get("/requests/pending", response_model=list[AccessRequestResponse])
def list_pending_requests(
    current_user: User = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    """
    Étape 2 du workflow : seul un admin peut consulter les demandes en
    attente de validation.
    """
    return access_request_service.list_pending(db)


@router.post("/requests/{request_id}/decision", response_model=AccessRequestResponse)
def decide_access_request(
    request_id: int,
    decision: AccessRequestDecision,
    current_user: User = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    """
    Étape 3-4 du workflow : l'admin approuve (génère un token temporaire
    lecture seule) ou refuse la demande.
    """
    if decision.approve:
        result = access_request_service.approve_request(db, request_id, current_user)
    else:
        result = access_request_service.reject_request(db, request_id, current_user)

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable")

    return result