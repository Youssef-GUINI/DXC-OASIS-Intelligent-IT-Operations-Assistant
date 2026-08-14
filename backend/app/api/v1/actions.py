"""
app/api/v1/actions.py

Route dédiée à la confirmation d'actions sensibles — jamais via un simple
message texte dans le chat. Le frontend affiche un bouton "Confirmer"
relié précisément à cet ActionRequest (action_type + target visibles avant
le clic).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.mcp.storage.client import storage_mcp_client  # instance existante (lifespan)
from app.schemas.incident import ActionRequestCreate, ActionRequestOut, ActionRequestRejection
from app.services import incident_service

router = APIRouter(prefix="/storage/actions", tags=["actions"])


@router.post("/", response_model=ActionRequestOut)
async def propose_action(
    payload: ActionRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Enregistre une action sensible proposée par l'agent (état pending).
    Appelé après analyze_incident, quand l'agent recommande par exemple un
    restore — jamais exécuté à ce stade.
    """
    try:
        return await incident_service.create_action_request(
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
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Point d'entrée du bouton "Confirmer" côté frontend. C'est le SEUL
    endroit du système qui déclenche confirm=True vers un tool MCP destructif.
    """
    try:
        return await incident_service.confirm_and_execute_action(
            db, action_id=action_id, user_id=current_user.id, mcp_client=storage_mcp_client,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{action_id}/reject", response_model=ActionRequestOut)
async def reject_action(
    action_id: uuid.UUID,
    payload: ActionRequestRejection,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await incident_service.reject_action_request(
            db, action_id=action_id, user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{action_id}", response_model=ActionRequestOut)
async def get_action(action_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from app.models.action_request import ActionRequest

    action = await db.get(ActionRequest, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action introuvable")
    return action