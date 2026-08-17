"""
app/api/v1/knowledge.py

Data Hub : l'ingénieur Storage ajoute ses propres documents à la base de
connaissances qu'OASIS interroge, les consulte et les supprime.
"""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.knowledge_document import KnowledgeDocumentOut
from app.services import knowledge_service
from app.services.knowledge_service import DocumentError

router = APIRouter(prefix="/storage/documents", tags=["data-hub"])

_storage_access = require_role("storage_engineer", "administrator")
_COLLECTION = "storage_kb"


@router.get("", response_model=list[KnowledgeDocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    return knowledge_service.list_documents(db, collection=_COLLECTION)


@router.post("", response_model=KnowledgeDocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    raw = await file.read()
    try:
        return knowledge_service.create_document(
            db,
            filename=file.filename or "document",
            content_type=file.content_type,
            raw=raw,
            user_id=current_user.id,
            collection=_COLLECTION,
        )
    except DocumentError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/{document_id}/content")
def read_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    try:
        document = knowledge_service.get_document(db, document_id)
        return {
            "id": str(document.id),
            "filename": document.filename,
            "text": knowledge_service.read_document_text(document),
        }
    except DocumentError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    try:
        knowledge_service.delete_document(db, document_id)
    except DocumentError as error:
        raise HTTPException(status_code=404, detail=str(error))
