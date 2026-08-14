"""
app/services/mcp_audit.py

Point d'écriture unique pour la table mcp_calls. Appelé depuis
StorageMCPClient.call_tool() (cf. patch client.py plus bas) — jamais
directement depuis agent.py, pour garantir qu'aucun appel n'échappe au log.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp_call import MCPCall, MCPCallStatus


async def log_mcp_call(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    persona: str,
    tool_name: str,
    arguments: dict[str, Any],
    result: Any = None,
    status: MCPCallStatus = MCPCallStatus.SUCCESS,
    error_message: str | None = None,
    action_request_id: uuid.UUID | None = None,
    correlation_id: uuid.UUID | None = None,
) -> MCPCall:
    call = MCPCall(
        user_id=user_id,
        persona=persona,
        tool_name=tool_name,
        arguments=arguments,
        result=result,
        status=status,
        error_message=error_message,
        action_request_id=action_request_id,
        correlation_id=correlation_id,
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return call


async def get_calls_for_correlation(db: AsyncSession, correlation_id: uuid.UUID) -> list[MCPCall]:
    """Récupère tous les appels MCP liés à une même analyse d'incident (traçabilité RCA)."""
    from sqlalchemy import select

    stmt = select(MCPCall).where(MCPCall.correlation_id == correlation_id).order_by(MCPCall.created_at)
    res = await db.execute(stmt)
    return list(res.scalars().all())