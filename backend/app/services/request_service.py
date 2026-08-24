"""
app/services/request_service.py

Demandes entre un ingénieur Storage et l'administrateur, dans les deux sens.

Deux règles portent toute la logique :

  - le **sens** est déduit du rôle de l'auteur, jamais fourni par le client :
    un ingénieur ne peut créer qu'une demande vers l'administrateur, et
    réciproquement. Le client ne peut donc pas fabriquer une demande qui
    semblerait venir de l'autre camp ;
  - seul le **destinataire** fait avancer le statut. Celui qui envoie une
    demande ne peut pas l'approuver lui-même.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.role import Role
from app.models.service_request import (
    RequestAttachment,
    RequestDirection,
    RequestEvent,
    RequestPriority,
    RequestStatus,
    ServiceRequest,
)
from app.models.user import User
from app.schemas.service_request import (
    RequestAttachmentOut,
    ServiceRequestCreate,
    ServiceRequestUpdate,
    ServiceRequestDetail,
    ServiceRequestOut,
    UserBrief,
)

ENGINEER_ROLE = "storage_engineer"
ADMIN_ROLE = "administrator"

# Transitions autorisees, par sens de circulation. Un statut dont l'ensemble
# est vide est terminal : une demande rejetee ou terminee ne bouge plus.
ALLOWED_TRANSITIONS: dict[RequestDirection, dict[RequestStatus, set[RequestStatus]]] = {
    RequestDirection.ENGINEER_TO_ADMIN: {
        RequestStatus.PENDING: {
            RequestStatus.IN_REVIEW,
            RequestStatus.APPROVED,
            RequestStatus.REJECTED,
        },
        RequestStatus.IN_REVIEW: {RequestStatus.APPROVED, RequestStatus.REJECTED},
        RequestStatus.APPROVED: {RequestStatus.COMPLETED},
        RequestStatus.REJECTED: set(),
        RequestStatus.COMPLETED: set(),
    },
    RequestDirection.ADMIN_TO_ENGINEER: {
        # Accuser reception est la voie normale, mais un ingenieur qui commence
        # aussitot le travail ne doit pas etre bloque par une etape rituelle.
        RequestStatus.PENDING: {RequestStatus.ACKNOWLEDGED, RequestStatus.IN_PROGRESS},
        RequestStatus.ACKNOWLEDGED: {RequestStatus.IN_PROGRESS, RequestStatus.COMPLETED},
        RequestStatus.IN_PROGRESS: {RequestStatus.COMPLETED},
        RequestStatus.COMPLETED: set(),
    },
}


# Statuts qui tranchent une demande. Y arriver fige `decided_at` : les
# transitions suivantes (Completed, par exemple) ne doivent pas faire glisser
# la date affichee a cote du verdict.
DECISION_STATUSES = {RequestStatus.APPROVED, RequestStatus.REJECTED}


# Une demande n'appartient plus tout a fait a son auteur des que le
# destinataire s'en est saisi : corriger l'enonce ou l'effacer apres coup
# reecrirait ce sur quoi l'autre s'est prononce. Tant qu'elle est PENDING,
# personne n'a encore rien decide.
EDITABLE_STATUSES = {RequestStatus.PENDING}

# Pieces jointes. Meme plafond que le Data Hub, mais un eventail de formats
# plus large : ce qui circule ici n'a pas vocation a etre indexe, seulement
# lu par l'autre partie.
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
ATTACHMENT_EXTENSIONS = {
    ".pdf", ".txt", ".md", ".log", ".csv", ".json", ".yaml", ".yml",
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".xlsx", ".xls", ".docx", ".doc", ".pptx", ".zip",
}


class RequestError(ValueError):
    """Refus métier : rôle non autorisé, transition invalide, demande absente."""


class RequestForbidden(RequestError):
    """L'utilisateur n'a pas le droit d'agir sur cette demande."""


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------

def _base_query(db: Session):
    # Ni les messages ni les evenements ne sont serialises : les charger
    # d'office ferait deux requetes de plus pour rien. Les pieces jointes, si :
    # la liste en affiche le nombre et le detail les enumere.
    return db.query(ServiceRequest).options(
        selectinload(ServiceRequest.creator).selectinload(User.role),
        selectinload(ServiceRequest.assignee).selectinload(User.role),
        selectinload(ServiceRequest.attachments).selectinload(RequestAttachment.uploader),
    )


def list_requests(
    db: Session, *, user: User, box: str, status: RequestStatus | None = None,
) -> list[ServiceRequest]:
    """`box` vaut 'sent' (demandes créées par moi) ou 'received' (qui me sont adressées)."""
    query = _base_query(db)
    if box == "sent":
        query = query.filter(ServiceRequest.created_by == user.id)
    elif box == "received":
        query = query.filter(ServiceRequest.assigned_to == user.id)
    else:
        raise RequestError("Boîte inconnue : attendu 'sent' ou 'received'.")

    if status is not None:
        query = query.filter(ServiceRequest.status == status)
    return query.order_by(ServiceRequest.created_at.desc()).all()


def get_request(db: Session, request_id: uuid.UUID, *, user: User) -> ServiceRequest:
    request = _base_query(db).filter(ServiceRequest.id == request_id).first()
    if request is None:
        raise RequestError("Demande introuvable.")
    if user.id not in (request.created_by, request.assigned_to):
        # Message volontairement identique au cas "introuvable" : inutile de
        # confirmer l'existence d'une demande qui ne regarde pas l'appelant.
        raise RequestForbidden("Demande introuvable.")
    return request


# ---------------------------------------------------------------------------
# Écriture
# ---------------------------------------------------------------------------

def _role_of(user: User) -> str:
    return user.role.name if user.role else ""


def _users_with_role(db: Session, role_name: str) -> list[User]:
    return (
        db.query(User)
        .join(Role)
        .filter(Role.name == role_name, User.is_active.is_(True))
        .order_by(User.id)
        .all()
    )


def list_recipients(db: Session, *, user: User) -> list[User]:
    """Destinataires possibles pour une nouvelle demande de cet utilisateur."""
    role = _role_of(user)
    if role == ENGINEER_ROLE:
        return _users_with_role(db, ADMIN_ROLE)
    if role == ADMIN_ROLE:
        return _users_with_role(db, ENGINEER_ROLE)
    raise RequestForbidden(
        "Seuls l'ingénieur Storage et l'administrateur utilisent les demandes."
    )


def create_request(
    db: Session, *, author: User, payload: ServiceRequestCreate,
) -> ServiceRequest:
    role = _role_of(author)
    if role == ENGINEER_ROLE:
        direction = RequestDirection.ENGINEER_TO_ADMIN
        target_role = ADMIN_ROLE
    elif role == ADMIN_ROLE:
        direction = RequestDirection.ADMIN_TO_ENGINEER
        target_role = ENGINEER_ROLE
    else:
        raise RequestForbidden(
            "Seuls l'ingénieur Storage et l'administrateur utilisent les demandes."
        )

    candidates = _users_with_role(db, target_role)
    if not candidates:
        raise RequestError(f"Aucun utilisateur actif avec le rôle '{target_role}'.")

    if payload.assigned_to is not None:
        assignee = next((u for u in candidates if u.id == payload.assigned_to), None)
        if assignee is None:
            raise RequestError(f"Le destinataire choisi n'est pas un '{target_role}' actif.")
    elif len(candidates) == 1:
        # Cas courant du projet : un seul administrateur. On evite de demander
        # a l'ingenieur de choisir dans une liste d'un seul element.
        assignee = candidates[0]
    else:
        raise RequestError("Plusieurs destinataires possibles : précisez 'assigned_to'.")

    # L'echeance n'a de sens que dans le sens administrateur -> ingenieur.
    deadline = payload.deadline if direction == RequestDirection.ADMIN_TO_ENGINEER else None

    request = ServiceRequest(
        direction=direction,
        title=payload.title.strip(),
        description=(payload.description or "").strip() or None,
        request_type=payload.request_type,
        priority=payload.priority or RequestPriority.MEDIUM,
        status=RequestStatus.PENDING,
        created_by=author.id,
        assigned_to=assignee.id,
        deadline=deadline,
    )
    db.add(request)
    db.flush()

    db.add(RequestEvent(
        request_id=request.id,
        actor_id=author.id,
        from_status=None,
        to_status=RequestStatus.PENDING,
        note="Demande créée",
    ))
    db.commit()
    return get_request(db, request.id, user=author)


def _owned_and_editable(db: Session, request_id: uuid.UUID, *, user: User) -> ServiceRequest:
    """Charge une demande que `user` a le droit de corriger ou de supprimer."""
    request = get_request(db, request_id, user=user)
    if request.created_by != user.id:
        raise RequestForbidden("Seul l'auteur d'une demande peut la modifier ou la supprimer.")
    if request.status not in EDITABLE_STATUSES:
        raise RequestError(
            "Cette demande a déjà été prise en charge : elle ne peut plus être "
            "modifiée ni supprimée."
        )
    return request


def update_request(
    db: Session, request_id: uuid.UUID, *, user: User, payload: ServiceRequestUpdate,
) -> ServiceRequest:
    """Corrige l'énoncé d'une demande encore en attente."""
    request = _owned_and_editable(db, request_id, user=user)
    changes = payload.model_dump(exclude_unset=True)

    if "title" in changes:
        title = (changes["title"] or "").strip()
        if not title:
            raise RequestError("Le titre ne peut pas être vide.")
        request.title = title
    if "description" in changes:
        request.description = (changes["description"] or "").strip() or None
    if "priority" in changes and changes["priority"] is not None:
        request.priority = changes["priority"]
    # Type et échéance ne valent que dans un sens chacun : on ignore
    # silencieusement celui qui n'a pas cours, comme le fait la création.
    if "request_type" in changes and request.direction == RequestDirection.ENGINEER_TO_ADMIN:
        request.request_type = changes["request_type"]
    if "deadline" in changes and request.direction == RequestDirection.ADMIN_TO_ENGINEER:
        request.deadline = changes["deadline"]

    if changes:
        # Trace d'audit : le statut ne bouge pas, seul l'énoncé change.
        db.add(RequestEvent(
            request_id=request.id,
            actor_id=user.id,
            from_status=request.status,
            to_status=request.status,
            note="Demande modifiée",
        ))
    db.commit()
    return get_request(db, request.id, user=user)


def delete_request(db: Session, request_id: uuid.UUID, *, user: User) -> None:
    """
    Retire une demande encore en attente.

    Messages, journal et pièces jointes suivent en cascade ; les binaires, eux,
    ne sont pas concernés par la cascade SQL et doivent être retirés à la main
    — sans quoi le disque garderait des fichiers que plus rien ne référence.
    """
    request = _owned_and_editable(db, request_id, user=user)
    stored_paths = [attachment.stored_path for attachment in request.attachments]
    db.delete(request)
    db.commit()
    for stored_path in stored_paths:
        _unlink(stored_path)


def update_status(
    db: Session,
    request_id: uuid.UUID,
    *,
    user: User,
    status: RequestStatus,
    note: str | None = None,
    administrator_response: str | None = None,
) -> ServiceRequest:
    request = get_request(db, request_id, user=user)

    if request.assigned_to != user.id:
        raise RequestForbidden(
            "Seul le destinataire d'une demande peut en faire évoluer le statut."
        )

    allowed = ALLOWED_TRANSITIONS[request.direction].get(request.status, set())
    if status not in allowed:
        readable = ", ".join(sorted(s.value for s in allowed)) or "aucune (statut final)"
        raise RequestError(
            f"Transition refusée : '{request.status.value}' vers '{status.value}'. "
            f"Transitions possibles : {readable}."
        )

    if administrator_response is not None:
        if _role_of(user) != ADMIN_ROLE:
            raise RequestForbidden(
                "Seul l'administrateur renseigne la réponse d'administration."
            )
        request.administrator_response = administrator_response.strip() or None

    previous = request.status
    request.status = status
    now = datetime.now(timezone.utc)
    if status in DECISION_STATUSES:
        request.decided_at = now
    if status == RequestStatus.ACKNOWLEDGED and request.acknowledged_at is None:
        request.acknowledged_at = now
    if status == RequestStatus.COMPLETED:
        request.completed_at = now

    db.add(RequestEvent(
        request_id=request.id,
        actor_id=user.id,
        from_status=previous,
        to_status=status,
        note=(note or "").strip() or None,
    ))
    db.commit()
    return get_request(db, request.id, user=user)


# ---------------------------------------------------------------------------
# Pièces jointes
# ---------------------------------------------------------------------------

def _attachment_dir() -> Path:
    """Sous-dossier dédié : les pièces jointes ne se mélangent pas au Data Hub."""
    directory = Path(settings.upload_dir) / "requests"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _unlink(stored_path: str) -> None:
    """Retire le binaire du disque, sans faire échouer l'appelant s'il a déjà disparu."""
    try:
        Path(stored_path).unlink(missing_ok=True)
    except OSError:
        # Fichier verrouillé ou volume en lecture seule : la ligne en base part
        # quand même, mieux vaut un orphelin sur disque qu'une suppression
        # bloquée côté utilisateur.
        pass


def add_attachment(
    db: Session,
    request_id: uuid.UUID,
    *,
    user: User,
    filename: str,
    content_type: str | None,
    raw: bytes,
) -> ServiceRequest:
    """
    Joint un fichier à une demande.

    Les deux parties peuvent déposer, à tout moment : c'est souvent après coup
    que le fichier arrive — le rapport qu'on demandait, la capture qui explique
    un refus. `get_request` a déjà vérifié que l'appelant est concerné.
    """
    request = get_request(db, request_id, user=user)

    if not raw:
        raise RequestError("Le fichier est vide.")
    if len(raw) > MAX_ATTACHMENT_BYTES:
        raise RequestError(
            f"Fichier trop volumineux ({len(raw) // 1024} Ko). Limite : "
            f"{MAX_ATTACHMENT_BYTES // (1024 * 1024)} Mo."
        )

    extension = Path(filename).suffix.lower()
    if extension not in ATTACHMENT_EXTENSIONS:
        raise RequestError(
            f"Format '{extension or 'inconnu'}' non pris en charge. "
            f"Formats acceptés : {', '.join(sorted(ATTACHMENT_EXTENSIONS))}."
        )

    attachment_id = uuid.uuid4()
    stored_path = _attachment_dir() / f"{attachment_id}{extension}"
    stored_path.write_bytes(raw)

    db.add(RequestAttachment(
        id=attachment_id,
        request_id=request.id,
        uploaded_by=user.id,
        # Path().name neutralise un nom du genre "../../etc/passwd" : seul le
        # dernier segment est conservé, et il ne sert qu'à l'affichage.
        filename=Path(filename).name[:255],
        stored_path=str(stored_path),
        content_type=content_type,
        size_bytes=len(raw),
    ))
    # Un dépôt fait vivre la demande : elle remonte comme récemment modifiée.
    request.updated_at = datetime.now(timezone.utc)
    db.commit()
    return get_request(db, request.id, user=user)


def get_attachment(
    db: Session, request_id: uuid.UUID, attachment_id: uuid.UUID, *, user: User,
) -> RequestAttachment:
    """Récupère une pièce jointe d'une demande que `user` a le droit de voir."""
    request = get_request(db, request_id, user=user)
    attachment = next((a for a in request.attachments if a.id == attachment_id), None)
    if attachment is None:
        raise RequestError("Pièce jointe introuvable.")
    return attachment


def delete_attachment(
    db: Session, request_id: uuid.UUID, attachment_id: uuid.UUID, *, user: User,
) -> ServiceRequest:
    """Retire une pièce jointe. Réservé à celui qui l'a déposée."""
    attachment = get_attachment(db, request_id, attachment_id, user=user)
    if attachment.uploaded_by != user.id:
        raise RequestForbidden("Seul l'auteur d'un dépôt peut le retirer.")

    stored_path = attachment.stored_path
    db.delete(attachment)
    db.commit()
    _unlink(stored_path)
    return get_request(db, request_id, user=user)


# ---------------------------------------------------------------------------
# Sérialisation
# ---------------------------------------------------------------------------

def serialize(request: ServiceRequest) -> ServiceRequestOut:
    return ServiceRequestOut(
        id=request.id,
        direction=request.direction,
        title=request.title,
        description=request.description,
        request_type=request.request_type,
        priority=request.priority,
        status=request.status,
        creator=UserBrief.of(request.creator),
        assignee=UserBrief.of(request.assignee),
        deadline=request.deadline,
        administrator_response=request.administrator_response,
        created_at=request.created_at,
        updated_at=request.updated_at,
        decided_at=request.decided_at,
        acknowledged_at=request.acknowledged_at,
        completed_at=request.completed_at,
        attachment_count=len(request.attachments),
    )


def serialize_detail(request: ServiceRequest) -> ServiceRequestDetail:
    """Detail d'une demande : la vue de liste, plus ses pieces jointes."""
    return ServiceRequestDetail(
        **serialize(request).model_dump(),
        attachments=[
            RequestAttachmentOut(
                id=attachment.id,
                filename=attachment.filename,
                content_type=attachment.content_type,
                size_bytes=attachment.size_bytes,
                uploader=UserBrief.of(attachment.uploader),
                created_at=attachment.created_at,
            )
            for attachment in request.attachments
        ],
    )
