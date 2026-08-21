"""
app/api/v1/reports.py

Téléchargement des rapports PDF. Routes en `def` synchrone : la génération lit
la capacité de la VM par SSH (paramiko, bloquant), FastAPI l'exécute donc dans
son threadpool plutôt que sur la boucle d'événements.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.user import User
from app.services import report_service

router = APIRouter(prefix="/storage/reports", tags=["reports"])

_storage_access = require_role("storage_engineer", "administrator")


def _pdf_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # Sans cet en-tête, le nom de fichier n'est pas lisible par le
            # frontend, qui lit la réponse en blob depuis un fetch authentifié.
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/global")
def download_global_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
) -> Response:
    """Rapport de l'environnement complet : capacité, sauvegardes, incidents."""
    content = report_service.build_global_report(db, author=current_user.email)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return _pdf_response(content, f"oasis-rapport-storage-{stamp}.pdf")


@router.get("/incidents/{ticket_id}")
def download_incident_report(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
) -> Response:
    """Rapport détaillé d'un incident, preuves relevées incluses."""
    content = report_service.build_incident_report(db, ticket_id, author=current_user.email)
    if content is None:
        raise HTTPException(status_code=404, detail="Ticket d'incident introuvable")
    return _pdf_response(content, f"oasis-incident-{ticket_id}.pdf")
