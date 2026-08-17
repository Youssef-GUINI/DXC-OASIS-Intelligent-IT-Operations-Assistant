"""
app/api/v1/actions.py

Route dédiée à la confirmation d'actions sensibles — jamais via un simple
message texte dans le chat. Le frontend affiche un bouton "Confirmer"
relié précisément à cet ActionRequest (action_type + target visibles avant
le clic).

CORRECTIF : db passait en AsyncSession alors que get_db() (app.api.deps)
renvoie une sqlalchemy.orm.Session classique -- incident_service est
maintenant sync, donc les `await` sur create_action_request/
reject_action_request/get_action ont été retirés. `confirm_and_execute_action`
reste `await` car il contient un vrai appel async vers mcp_client.call_tool.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.mcp.storage.client import storage_mcp_client  # instance existante (lifespan)
from app.models.action_request import ActionRequest, ActionRequestStatus
from app.schemas.incident import ActionRequestCreate, ActionRequestOut, ActionRequestRejection
from app.services import incident_service

router = APIRouter(prefix="/storage/actions", tags=["actions"])


@router.get("", response_model=list[ActionRequestOut])
def list_my_actions(
    status: Optional[ActionRequestStatus] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Demandes soumises par l'utilisateur courant — alimente la page "My Requests".
    Volontairement filtré sur requested_by : un ingénieur ne voit que les siennes.
    """
    query = db.query(ActionRequest).filter(ActionRequest.requested_by == current_user.id)
    if status is not None:
        query = query.filter(ActionRequest.status == status)
    return (
        query.order_by(ActionRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("/", response_model=ActionRequestOut)
def propose_action(
    payload: ActionRequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Enregistre une action sensible proposée par l'agent (état pending).
    Appelé après analyze_incident, quand l'agent recommande par exemple un
    restore — jamais exécuté à ce stade.
    """
    try:
        return incident_service.create_action_request(
            db,
            user_id=current_user.id,
            action_type=payload.action_type,
            target=payload.target,
            parameters=payload.parameters,
            incident_ticket_id=payload.incident_ticket_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{action_id}/confirm", response_model=ActionRequestOut)
async def confirm_action(
    action_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Point d'entrée du bouton "Confirmer" côté frontend. C'est le SEUL
    endroit du système qui déclenche confirm=True vers un tool MCP destructif.
    Reste `async def` + `await` : confirm_and_execute_action fait un vrai
    appel MCP asynchrone (stdio), même si ses accès DB internes sont sync.
    """
    try:
        return await incident_service.confirm_and_execute_action(
            db, action_id=action_id, user_id=current_user.id, mcp_client=storage_mcp_client,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{action_id}/reject", response_model=ActionRequestOut)
def reject_action(
    action_id: uuid.UUID,
    payload: ActionRequestRejection,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return incident_service.reject_action_request(
            db, action_id=action_id, user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{action_id}", response_model=ActionRequestOut)
def get_action(
    action_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),  # AJOUTÉ -- absent dans l'original, cf. remarque précédente
):
    from app.models.action_request import ActionRequest

    action = db.get(ActionRequest, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action introuvable")
    return action