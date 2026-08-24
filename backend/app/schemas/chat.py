"""Schémas du chat Storage."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.chat_message import TITLE_MAX_LENGTH
from app.schemas.incident import ActionRequestOut


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    # Actions que ce message propose. L'interface les rend sous forme de
    # boutons Confirmer/Rejeter : une remédiation annoncée en texte seul
    # laisserait croire qu'elle a été lancée, alors qu'elle attend un clic.
    action_requests: list[ActionRequestOut] = []

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    # Renseigné pour un fil ouvert depuis un incident : l'interface y affiche
    # le numéro du ticket et un retour vers sa fiche.
    incident_ticket_id: uuid.UUID | None = None

    class Config:
        from_attributes = True


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)


class ChatRequest(BaseModel):
    message: str
    # Absent : le message ouvre une nouvelle conversation. C'est le cas du
    # premier message, et de celui qui suit un clic sur « New chat ».
    conversation_id: int | None = None


class ChatTurnOut(BaseModel):
    """Le tour complet, avec le fil auquel il appartient."""

    response: str
    conversation: ConversationOut
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
