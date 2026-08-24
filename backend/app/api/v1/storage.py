"""
app/api/v1/storage.py

Chat Storage : les conversations conservées côté serveur, et l'échange avec
la persona.

Un fil survit à un changement de page comme à une reconnexion, et l'agent
reçoit les derniers messages du fil en contexte au lieu de repartir de zéro à
chaque question. Un utilisateur ne voit jamais que ses propres conversations :
chaque route repasse par _require_conversation, qui filtre sur son identité.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.chat_message import ChatConversation
from app.models.user import User
from app.personas.storage.agent import storage_persona
from app.schemas.chat import (
    ChatMessageOut,
    ChatRequest,
    ChatTurnOut,
    ConversationOut,
    ConversationUpdate,
)
from app.services import chat_service, incident_investigation, incident_service

router = APIRouter(prefix="/storage", tags=["storage"])

_storage_access = require_role("storage_engineer", "administrator")


def _require_conversation(db: Session, user: User, conversation_id: int) -> ChatConversation:
    """
    Le fil demandé, ou 404 -- y compris s'il appartient à un collègue : dire
    « interdit » plutôt qu'« introuvable » confirmerait son existence.
    """
    conversation = chat_service.get_conversation(db, user.id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return conversation


@router.get("/chat/conversations", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    return chat_service.list_conversations(db, current_user.id)


@router.get("/chat/conversations/{conversation_id}/messages", response_model=list[ChatMessageOut])
def conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    conversation = _require_conversation(db, current_user, conversation_id)
    return chat_service.list_messages(db, conversation.id)


@router.patch("/chat/conversations/{conversation_id}", response_model=ConversationOut)
def rename_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    conversation = _require_conversation(db, current_user, conversation_id)
    return chat_service.rename_conversation(db, conversation, payload.title)


@router.delete("/chat/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    conversation = _require_conversation(db, current_user, conversation_id)
    chat_service.delete_conversation(db, conversation)


@router.post("/chat", response_model=ChatTurnOut)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_storage_access),
):
    # Sans conversation_id, le message ouvre un nouveau fil.
    conversation: ChatConversation | None = None
    history: list[dict[str, str]] = []
    if payload.conversation_id is not None:
        conversation = _require_conversation(db, current_user, payload.conversation_id)
        history = chat_service.history_for_llm(db, conversation.id)

    # Un fil ouvert depuis un incident garde son contexte à chaque tour : sans
    # cela, la deuxième question de l'investigation retomberait sur un agent
    # qui ne sait plus de quel ticket on parle, et les actions qu'il proposerait
    # ne seraient rattachées à rien.
    incident = None
    if conversation is not None and conversation.incident_ticket_id is not None:
        ticket = incident_service.get_ticket(db, conversation.incident_ticket_id)
        if ticket is not None:
            incident = incident_investigation.context_for(ticket)

    # created_by=current_user.id -- permet à agent.py de créer automatiquement
    # un IncidentTicket (attribué à cet utilisateur) si une anomalie
    # HIGH/CRITICAL est détectée pendant la conversation.
    turn = await storage_persona.handle_message(
        payload.message,
        created_by=current_user.id,
        history=history,
        incident=incident,
    )

    # Rien n'est écrit avant la réponse : si l'agent échoue, l'exception
    # remonte sans laisser dans la liste un fil vide, ni dans un fil existant
    # une question restée sans réponse.
    if conversation is None:
        conversation = chat_service.create_conversation(
            db, current_user.id, title=chat_service.title_from_message(payload.message)
        )

    user_message, assistant_message = chat_service.save_turn(
        db, conversation, question=payload.message, answer=turn.text
    )
    chat_service.attach_actions(db, assistant_message, turn.proposed_action_ids)

    return ChatTurnOut(
        response=turn.text,
        conversation=ConversationOut.model_validate(conversation),
        user_message=ChatMessageOut.model_validate(user_message),
        assistant_message=ChatMessageOut.model_validate(assistant_message),
    )
