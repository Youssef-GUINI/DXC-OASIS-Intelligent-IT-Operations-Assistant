from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.personas.linux.agent import linux_persona

router = APIRouter(prefix="/linux", tags=["linux"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, current_user: User = Depends(get_current_user)):
    answer = linux_persona.handle_message(payload.message)
    return ChatResponse(response=answer)
