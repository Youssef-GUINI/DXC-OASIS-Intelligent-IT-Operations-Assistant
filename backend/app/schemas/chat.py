"""Schémas du chat Storage."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.chat_message import TITLE_MAX_LENGTH


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

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
