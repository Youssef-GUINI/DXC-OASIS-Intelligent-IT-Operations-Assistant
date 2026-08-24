"""
app/api/v1/requests.py

Canal de demandes entre l'ingénieur Storage et l'administrateur.

Les routes sont symétriques : chacun voit ses demandes envoyées ('sent') et
celles qu'il a reçues ('received'). Ce qui change selon le rôle, c'est le sens
que prend une demande créée et les transitions de statut autorisées — décidé
dans request_service, jamais ici.
"""

import uuid
from pathlib import Path

from fastapi import (
    APIRouter, Depends, File, HTTPException, Query, Response, UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.service_request import RequestStatus
from app.models.user import User
from app.schemas.service_request import (
    RequestStatusUpdate,
    ServiceRequestCreate,
    ServiceRequestDetail,
    ServiceRequestOut,
    ServiceRequestUpdate,
    UserBrief,
)
from app.services import request_service
from app.services.request_service import RequestError, RequestForbidden

router = APIRouter(prefix="/requests", tags=["requests"])

# Le Linux Engineer n'a pas accès à ce canal : il relie l'ingénieur Storage
# et l'administrateur, et rien d'autre.
_participants = require_role("storage_engineer", "administrator")


def _handle(error: RequestError) -> HTTPException:
    if isinstance(error, RequestForbidden):
        return HTTPException(status_code=403, detail=str(error))
    return HTTPException(status_code=400, detail=str(error))


@router.get("", response_model=list[ServiceRequestOut])
def list_requests(
    box: str = Query("sent", pattern="^(sent|received)$"),
    status: RequestStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(_participants),
):
    """'sent' alimente « My Requests », 'received' alimente « Requests From … »."""
    try:
        found = request_service.list_requests(
            db, user=current_user, box=box, status=status,
        )
    except RequestError as error:
        raise _handle(error)
    return [request_service.serialize(request) for request in found]


@router.get("/recipients", response_model=list[UserBrief])
def list_recipients(
    db: Session = Depends(get_db),
    current_user: User = Depends(_participants),
):
    """Destinataires possibles — dépend du rôle de l'appelant."""
    try:
        users = request_service.list_recipients(db, user=current_user)
    except RequestError as error:
        raise _handle(error)
    return [UserBrief.of(user) for user in users]


@router.post("", response_model=ServiceRequestDetail, status_code=201)
def create_request(
    payload: ServiceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_participants),
):
    try:
        request = request_service.create_request(db, author=current_user, payload=payload)
    except RequestError as error:
        raise _handle(error)
    return request_service.serialize_detail(request)


@router.get("/{request_id}", response_model=ServiceRequestDetail)
def get_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_participants),
):
    """La demande seule : son contenu, son statut et la date de sa décision."""
    try:
        request = request_service.get_request(db, request_id, user=current_user)
    except RequestForbidden as error:
        raise HTTPException(status_code=404, detail=str(error))
    except RequestError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return request_service.serialize_detail(request)


@router.patch("/{request_id}", response_model=ServiceRequestDetail)
def update_request(
    request_id: uuid.UUID,
    payload: ServiceRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_participants),
):
    """
    Corrige une demande : titre, description, type, priorité, échéance.

    Réservé à son auteur, et seulement tant que le destinataire ne s'en est
    pas saisi — le statut, lui, passe par la route dédiée ci-dessous.
    """
    try:
        request = request_service.update_request(
            db, request_id, user=current_user, payload=payload,
        )
    except RequestError as error:
        raise _handle(error)
    return request_service.serialize_detail(request)


@router.delete("/{request_id}", status_code=204)
def delete_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_participants),
):
    """Retire une demande envoyée par erreur, tant qu'elle est en attente."""
    try:
        request_service.delete_request(db, request_id, user=current_user)
    except RequestError as error:
        raise _handle(error)
    return Response(status_code=204)


@router.patch("/{request_id}/status", response_model=ServiceRequestDetail)
def update_status(
    request_id: uuid.UUID,
    payload: RequestStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_participants),
):
    """
    Fait avancer une demande. Couvre les deux sens :
    l'administrateur passe In Review / Approved / Rejected sur ce qu'il reçoit,
    l'ingénieur passe Acknowledged / In Progress / Completed sur ce qu'il reçoit.
    """
    try:
        request = request_service.update_status(
            db,
            request_id,
            user=current_user,
            status=payload.status,
            note=payload.note,
            administrator_response=payload.administrator_response,
        )
    except RequestError as error:
        raise _handle(error)
    return request_service.serialize_detail(request)


# ---------------------------------------------------------------------------
# Pièces jointes
# ---------------------------------------------------------------------------

@router.post("/{request_id}/attachments", response_model=ServiceRequestDetail, status_code=201)
async def add_attachment(
    request_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(_participants),
):
    """
    Dépose un fichier sur une demande.

    Renvoie la demande complète plutôt que la seule pièce jointe : l'interface
    réaffiche la liste des fichiers dans la foulée, sans second appel.
    """
    raw = await file.read()
    try:
        request = request_service.add_attachment(
            db,
            request_id,
            user=current_user,
            filename=file.filename or "fichier",
            content_type=file.content_type,
            raw=raw,
        )
    except RequestError as error:
        raise _handle(error)
    return request_service.serialize_detail(request)


@router.get("/{request_id}/attachments/{attachment_id}")
def download_attachment(
    request_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_participants),
):
    """Renvoie le binaire, sous le nom que le déposant lui a donné."""
    try:
        attachment = request_service.get_attachment(
            db, request_id, attachment_id, user=current_user,
        )
    except RequestError as error:
        raise _handle(error)

    path = Path(attachment.stored_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable sur le serveur.")
    return FileResponse(
        path,
        media_type=attachment.content_type or "application/octet-stream",
        filename=attachment.filename,
    )


@router.delete("/{request_id}/attachments/{attachment_id}", response_model=ServiceRequestDetail)
def delete_attachment(
    request_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_participants),
):
    """Retire un fichier déposé. Réservé à celui qui l'a déposé."""
    try:
        request = request_service.delete_attachment(
            db, request_id, attachment_id, user=current_user,
        )
    except RequestError as error:
        raise _handle(error)
    return request_service.serialize_detail(request)
