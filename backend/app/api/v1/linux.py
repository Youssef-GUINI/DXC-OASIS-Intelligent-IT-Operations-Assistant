from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_role
from app.models.user import User
from app.personas.linux.agent import linux_persona

router = APIRouter(prefix="/linux", tags=["linux"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(require_role("linux_engineer", "administrator")),
):
    answer = linux_persona.handle_message(payload.message)
    return ChatResponse(response=answer)