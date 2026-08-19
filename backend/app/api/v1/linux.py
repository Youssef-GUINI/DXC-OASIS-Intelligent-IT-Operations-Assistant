from fastapi.responses import FileResponse
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.report_service import create_report_for_incident, create_global_report
from app.dashboard.kpi_service import get_linux_kpis
from app.schemas.dashboard import LinuxKPIs
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.personas.linux.agent import linux_persona
from app.services.incident_service import (
    save_incident,
    list_incidents,
    resolve_incident,
)
from app.schemas.incident import IncidentResponse


router = APIRouter(prefix="/linux", tags=["linux"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    answer = linux_persona.handle_message(payload.message, db=db)

    # IMPORTANT :
    # Une conversation normale ne doit PAS être enregistrée
    # automatiquement comme un incident.
    #
    # Les incidents système sont créés par le monitoring/scheduler.
    # Les incidents utilisateur devront être créés explicitement
    # dans une logique dédiée si nécessaire.

    return ChatResponse(response=answer)


@router.get("/incidents", response_model=list[IncidentResponse])
def get_incidents(
    status_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_incidents(
        db,
        status=status_filter,
        persona="linux_persona",
    )


@router.patch(
    "/incidents/{incident_id}/resolve",
    response_model=IncidentResponse,
)
def resolve_incident_route(
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    incident = resolve_incident(db, incident_id)

    if not incident:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Incident introuvable",
        )

    return incident


@router.get("/dashboard/kpis", response_model=LinuxKPIs)
def get_dashboard_kpis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_linux_kpis(db)


@router.post("/incidents/{incident_id}/report")
def generate_report(
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = create_report_for_incident(
        db,
        incident_id,
        current_user.id,
    )

    if not report:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Incident introuvable",
        )

    return FileResponse(
        path=report.file_path,
        media_type="application/pdf",
        filename=f"rapport_incident_{incident_id}.pdf",
    )
@router.post("/reports/global")
def generate_global_report_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = create_global_report(db, current_user.id)
    return FileResponse(
        path=report.file_path,
        media_type="application/pdf",
        filename="rapport_global_linux.pdf",
    )
