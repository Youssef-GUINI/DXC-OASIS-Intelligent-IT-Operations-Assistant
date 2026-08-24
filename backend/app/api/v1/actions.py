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

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.mcp.storage.client import StorageMCPClient
from app.models.action_request import ActionRequest, ActionRequestStatus
from app.schemas.incident import ActionRequestCreate, ActionRequestOut, ActionRequestRejection
from app.services import incident_service, incident_verification

logger = logging.getLogger(__name__)

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

    CORRECTIF : cette route utilisait une instance module-level de
    StorageMCPClient dont personne n'appelait jamais start() -- ni le lifespan
    de main.py, ni cette route. call_tool() levait donc systématiquement
    "Storage MCP indisponible", l'action retombait en FAILED et l'API répondait
    quand même 200 : le seul chemin autorisé pour exécuter une action
    destructive ne fonctionnait pas.

    Le client est maintenant démarré pour la durée de l'appel puis fermé,
    exactement comme le fait le persona Storage (app/personas/storage/agent.py).
    Une confirmation est un clic humain, donc rare : le coût du démarrage du
    sous-processus est négligeable, et on évite le sous-processus partagé qui
    reste mort jusqu'au prochain redémarrage du backend s'il tombe.
    """
    mcp = StorageMCPClient()
    try:
        await mcp.start()
    except Exception as error:  # noqa: BLE001 -- sous-processus MCP non démarrable
        # Rien n'a encore été modifié : l'action reste PENDING et reste
        # rejouable. On le dit explicitement au frontend plutôt que de la
        # marquer FAILED derrière un 200.
        raise HTTPException(
            status_code=503,
            detail=f"Storage MCP server unavailable, action not executed: {error}",
        )

    try:
        action = await incident_service.confirm_and_execute_action(
            db, action_id=action_id, user_id=current_user.id, mcp_client=mcp,
        )
        await _close_the_loop(db, action, user=current_user, mcp=mcp)
        return action
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        await mcp.stop()


async def _close_the_loop(db: Session, action: ActionRequest, *, user, mcp) -> None:
    """
    Dernier maillon du cycle : vérifier sur la VM, puis clore si c'est vrai.

    Une action exécutée sans erreur ne prouve rien : `systemctl start` réussit
    à lancer un job qui échouera trois secondes plus tard. On relit donc
    l'indicateur qui avait ouvert le ticket, et on ne referme que s'il est
    redevenu sain -- sinon le ticket reste ouvert en disant pourquoi.

    Aucun échec ici ne doit faire échouer la requête : l'action, elle, a bien
    eu lieu, et la surveillance périodique repassera vérifier.
    """
    if action.incident_ticket_id is None:
        return

    ticket = incident_service.get_ticket(db, action.incident_ticket_id)
    if ticket is None:
        return

    who = user.full_name or user.email
    label = f"{action.action_type} sur {action.target}"

    try:
        if action.status == ActionRequestStatus.FAILED:
            reason = (action.result or {}).get("error", "unknown reason")
            incident_service.add_note(
                db, ticket_id=ticket.id, author_id=user.id,
                content=f'Action "{label}" confirmed by {who} but failed: {reason}',
            )
            return

        verdict = await incident_verification.verify(
            ticket, mcp=mcp, db=db, user_id=user.id
        )
        incident_service.add_note(
            db, ticket_id=ticket.id, author_id=user.id,
            content=f'Action "{label}" confirmed by {who} and executed. {verdict.detail}',
        )
        if verdict.resolved:
            incident_service.resolve_ticket(
                db, ticket, author_id=user.id,
                reason=f"Incident closed automatically: {verdict.detail}",
            )
    except Exception:  # noqa: BLE001
        logger.exception("Clôture du cycle impossible pour %s", ticket.ticket_number)


@router.post("/{action_id}/reject", response_model=ActionRequestOut)
def reject_action(
    action_id: uuid.UUID,
    payload: ActionRequestRejection,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        action = incident_service.reject_action_request(
            db, action_id=action_id, user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Un rejet est une décision, pas un non-événement : il doit rester lisible
    # dans l'historique du ticket, avec son motif quand il y en a un.
    if action.incident_ticket_id is not None:
        who = current_user.full_name or current_user.email
        motive = f" Reason: {payload.reason}" if payload.reason else ""
        incident_service.add_note(
            db,
            ticket_id=action.incident_ticket_id,
            author_id=current_user.id,
            content=f'Action "{action.action_type} on {action.target}" '
                    f"rejected by {who}.{motive}",
        )
    return action


@router.get("/{action_id}", response_model=ActionRequestOut)
def get_action(
    action_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),  # AJOUTÉ -- absent dans l'original, cf. remarque précédente
):
    from app.models.action_request import ActionRequest

    action = db.get(ActionRequest, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action