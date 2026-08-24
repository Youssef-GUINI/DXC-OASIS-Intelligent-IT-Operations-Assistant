"""
app/services/chat_service.py

Persistance des conversations entre un ingénieur et OASIS.

Un utilisateur mène autant de fils qu'il veut : le diagnostic d'un incident
d'un côté, une question de capacité de l'autre, chacun avec son contexte. Une
conversation appartient à un utilisateur et n'est lisible que par lui -- toutes
les fonctions prennent donc user_id et filtrent dessus, y compris pour lire un
fil désigné par son identifiant.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

import uuid

from app.models.action_request import ActionRequest
from app.models.chat_message import (
    ROLE_ASSISTANT,
    ROLE_USER,
    TITLE_MAX_LENGTH,
    ChatConversation,
    ChatMessage,
)

# Au-delà, on ne renvoie que la fin du fil : personne ne remonte deux cents
# messages dans l'interface, et les charger tous coûterait pour rien.
MAX_HISTORY = 200

# Contexte réinjecté dans le prompt. Volontairement court : les réponses de
# l'agent contiennent des relevés MCP entiers, un fil trop long sature la
# fenêtre du modèle et fait dériver la réponse.
LLM_CONTEXT_MESSAGES = 10

DEFAULT_TITLE = "New conversation"


def title_from_message(message: str) -> str:
    """
    Libellé de conversation déduit de la première question.

    On coupe à la fin d'un mot : « Which volumes are near… » se relit, pas
    « Which volumes are near capa ».
    """
    condensed = " ".join(message.split())
    if not condensed:
        return DEFAULT_TITLE
    if len(condensed) <= TITLE_MAX_LENGTH:
        return condensed

    truncated = condensed[: TITLE_MAX_LENGTH - 1]
    cut = truncated.rfind(" ")
    if cut > TITLE_MAX_LENGTH // 2:
        truncated = truncated[:cut]
    return f"{truncated.rstrip()}…"


# --- Conversations --------------------------------------------------------


def list_conversations(db: Session, user_id: int) -> list[ChatConversation]:
    """Les fils de l'utilisateur, le plus récemment utilisé en tête."""
    return (
        db.query(ChatConversation)
        .filter(ChatConversation.user_id == user_id)
        .order_by(ChatConversation.updated_at.desc(), ChatConversation.id.desc())
        .all()
    )


def get_conversation(db: Session, user_id: int, conversation_id: int) -> ChatConversation | None:
    """Le fil demandé, ou None s'il n'existe pas ou appartient à quelqu'un d'autre."""
    return (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user_id,
        )
        .first()
    )


def create_conversation(db: Session, user_id: int, title: str | None = None) -> ChatConversation:
    conversation = ChatConversation(user_id=user_id, title=title or DEFAULT_TITLE)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def rename_conversation(db: Session, conversation: ChatConversation, title: str) -> ChatConversation:
    """
    Renomme sans toucher à updated_at : renommer n'est pas discuter, le fil ne
    doit pas remonter en tête de liste pour autant.
    """
    conversation.title = title.strip()[:TITLE_MAX_LENGTH] or DEFAULT_TITLE
    db.commit()
    db.refresh(conversation)
    return conversation


def delete_conversation(db: Session, conversation: ChatConversation) -> None:
    """Supprime le fil ; ses messages suivent (ON DELETE CASCADE)."""
    db.delete(conversation)
    db.commit()


# --- Messages -------------------------------------------------------------


def attach_actions(
    db: Session, message: ChatMessage, action_ids: list[uuid.UUID]
) -> ChatMessage:
    """
    Rattache au message les actions qu'il propose.

    Le lien ne peut être posé qu'après coup : l'agent enregistre les
    propositions pendant son tour, alors que le message qui les annonce
    n'existe pas encore et n'a donc pas d'identifiant. Sans ce rattachement,
    les boutons Confirmer/Rejeter disparaîtraient au rechargement du fil,
    alors que les actions, elles, resteraient en attente en base.
    """
    if not action_ids:
        return message

    db.execute(
        ActionRequest.__table__.update()
        .where(ActionRequest.id.in_(action_ids))
        .values(chat_message_id=message.id)
    )
    db.commit()
    db.refresh(message)
    return message


def list_messages(db: Session, conversation_id: int, limit: int = MAX_HISTORY) -> list[ChatMessage]:
    """Les messages du fil, du plus ancien au plus récent."""
    recent = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(recent))


def history_for_llm(db: Session, conversation_id: int) -> list[dict[str, str]]:
    """Les derniers messages du fil, au format attendu par le client Groq."""
    messages = list_messages(db, conversation_id, limit=LLM_CONTEXT_MESSAGES)
    return [{"role": message.role, "content": message.content} for message in messages]


def save_turn(
    db: Session, conversation: ChatConversation, *, question: str, answer: str
) -> tuple[ChatMessage, ChatMessage]:
    """
    Enregistre la question et la réponse en une seule transaction.

    Les deux messages sont écrits ensemble, après que l'agent a répondu : un
    échec de l'appel LLM ne doit pas laisser dans le fil une question restée
    sans réponse, que le rechargement afficherait comme un blanc inexplicable.
    """
    user_message = ChatMessage(
        conversation_id=conversation.id, role=ROLE_USER, content=question
    )
    assistant_message = ChatMessage(
        conversation_id=conversation.id, role=ROLE_ASSISTANT, content=answer
    )
    db.add_all([user_message, assistant_message])

    # Ajouter un message ne modifie pas la ligne de la conversation : sans
    # cette écriture explicite, updated_at resterait à la date de création et
    # l'ordre de la liste latérale ne bougerait plus.
    conversation.updated_at = func.now()

    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    db.refresh(conversation)
    return user_message, assistant_message
