from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_role
from app.models.user import User
from app.personas.storage.agent import storage_persona

router = APIRouter(prefix="/storage", tags=["storage"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(require_role("storage_engineer", "administrator")),
):
    answer = await storage_persona.handle_message(payload.message)
    return ChatResponse(response=answer)