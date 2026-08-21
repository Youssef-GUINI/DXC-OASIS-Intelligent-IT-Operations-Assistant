"""
app/services/search_service.py

Recherche globale de la barre du haut.

Elle interroge ce que l'ingénieur a réellement sous la main : ses incidents,
ses demandes d'action, ses documents et ses conversations. Les volumes et les
relevés de capacité en sont volontairement absents : ils ne vivent pas en base
mais derrière un appel MCP à la VM, qu'on ne peut pas déclencher à chaque
frappe -- le dashboard reste l'endroit où on les lit.

Les résultats sont typés et rendus tels quels : c'est le frontend qui sait
vers quelle page mène un incident ou une conversation, la base n'a pas à
connaître les routes de l'interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.action_request import ActionRequest
from app.models.chat_message import ChatConversation, ChatMessage
from app.models.incident_ticket import IncidentTicket
from app.models.knowledge_document import KnowledgeDocument
from app.models.user import User

MIN_QUERY_LENGTH = 2
DEFAULT_LIMIT_PER_TYPE = 5
SNIPPET_RADIUS = 60


@dataclass
class SearchHit:
    type: str
    id: str
    title: str
    subtitle: str | None
    timestamp: datetime | None


def _pattern(query: str) -> str:
    """
    Motif ILIKE échappé.

    Sans échappement, un « % » tapé dans la barre de recherche deviendrait un
    joker et remonterait toute la base ; un « _ » remplacerait n'importe quel
    caractère.
    """
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _snippet(text: str, query: str) -> str:
    """Extrait du texte autour du terme trouvé, pour montrer le contexte du match."""
    condensed = " ".join(text.split())
    position = condensed.lower().find(query.lower())
    if position == -1:
        return condensed[: SNIPPET_RADIUS * 2] + ("…" if len(condensed) > SNIPPET_RADIUS * 2 else "")

    start = max(0, position - SNIPPET_RADIUS)
    end = min(len(condensed), position + len(query) + SNIPPET_RADIUS)
    return (
        ("…" if start > 0 else "")
        + condensed[start:end]
        + ("…" if end < len(condensed) else "")
    )


def _incidents(db: Session, query: str, limit: int) -> list[SearchHit]:
    pattern = _pattern(query)
    tickets = (
        db.query(IncidentTicket)
        .filter(
            or_(
                IncidentTicket.ticket_number.ilike(pattern, escape="\\"),
                IncidentTicket.title.ilike(pattern, escape="\\"),
                IncidentTicket.description.ilike(pattern, escape="\\"),
                IncidentTicket.affected_system.ilike(pattern, escape="\\"),
            )
        )
        .order_by(IncidentTicket.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        SearchHit(
            type="incident",
            # L'UUID, et non le numéro affiché : la page Incidents recharge le
            # ticket par la route /incidents/{id}, ce qui l'ouvre même quand
            # il ne figure pas dans la liste actuellement filtrée.
            id=str(ticket.id),
            title=f"{ticket.ticket_number} · {ticket.title}",
            subtitle=f"{ticket.severity.value} · {ticket.status.value} · {ticket.affected_system}",
            timestamp=ticket.created_at,
        )
        for ticket in tickets
    ]


def _requests(db: Session, user_id: int, query: str, limit: int) -> list[SearchHit]:
    pattern = _pattern(query)
    requests = (
        db.query(ActionRequest)
        .filter(
            ActionRequest.requested_by == user_id,
            or_(
                ActionRequest.action_type.ilike(pattern, escape="\\"),
                ActionRequest.target.ilike(pattern, escape="\\"),
            ),
        )
        .order_by(ActionRequest.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        SearchHit(
            type="request",
            id=str(request.id),
            title=f"{request.action_type.replace('_', ' ').capitalize()} · {request.target}",
            subtitle=request.status.value,
            timestamp=request.created_at,
        )
        for request in requests
    ]


def _documents(db: Session, query: str, limit: int) -> list[SearchHit]:
    pattern = _pattern(query)
    documents = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.filename.ilike(pattern, escape="\\"))
        .order_by(KnowledgeDocument.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        SearchHit(
            type="document",
            id=str(document.id),
            title=document.filename,
            subtitle=f"{document.status.value} · {document.chunk_count} chunks",
            timestamp=document.created_at,
        )
        for document in documents
    ]


def _conversations(db: Session, user_id: int, query: str, limit: int) -> list[SearchHit]:
    """
    Fils de l'utilisateur dont le titre ou l'un des messages correspond.

    Un fil trouvé par son contenu affiche l'extrait qui l'a fait sortir :
    « Conversation du 12 » ne dirait pas pourquoi elle est là.
    """
    pattern = _pattern(query)

    matched_messages = (
        db.query(ChatMessage)
        .join(ChatConversation, ChatMessage.conversation_id == ChatConversation.id)
        .filter(
            ChatConversation.user_id == user_id,
            ChatMessage.content.ilike(pattern, escape="\\"),
        )
        .order_by(ChatMessage.id.desc())
        .limit(limit * 4)
        .all()
    )
    snippets: dict[int, str] = {}
    for message in matched_messages:
        snippets.setdefault(message.conversation_id, _snippet(message.content, query))

    matches = [ChatConversation.title.ilike(pattern, escape="\\")]
    if snippets:
        matches.append(ChatConversation.id.in_(list(snippets)))

    conversations = (
        db.query(ChatConversation)
        .filter(ChatConversation.user_id == user_id, or_(*matches))
        .order_by(ChatConversation.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        SearchHit(
            type="conversation",
            id=str(conversation.id),
            title=conversation.title,
            subtitle=snippets.get(conversation.id),
            timestamp=conversation.updated_at,
        )
        for conversation in conversations
    ]


def search(
    db: Session, user: User, query: str, limit_per_type: int = DEFAULT_LIMIT_PER_TYPE
) -> list[SearchHit]:
    """
    Résultats groupés par type, dans l'ordre où l'ingénieur les cherche.

    Une requête d'un seul caractère ne discrimine rien : elle renverrait la
    moitié de la base pour rien.
    """
    cleaned = query.strip()
    if len(cleaned) < MIN_QUERY_LENGTH:
        return []

    return [
        *_incidents(db, cleaned, limit_per_type),
        *_requests(db, user.id, cleaned, limit_per_type),
        *_conversations(db, user.id, cleaned, limit_per_type),
        *_documents(db, cleaned, limit_per_type),
    ]
