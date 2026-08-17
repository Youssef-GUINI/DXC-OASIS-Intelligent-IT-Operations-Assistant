"""
app/services/mcp_audit.py

Point d'écriture unique pour la table mcp_calls. Appelé depuis
StorageMCPClient.call_tool() — jamais directement depuis agent.py, pour
garantir qu'aucun appel n'échappe au log.

CORRECTIF : ce module était écrit pour AsyncSession (`await db.commit()`)
alors que session.py fournit une sqlalchemy.orm.Session synchrone. Sur une
session sync, `db.commit()` renvoie None et `await None` lève un TypeError :
l'audit n'aurait jamais pu fonctionner. Fonctions passées en `def` sync, comme
le reste des services du projet.

`user_id` est un `int` : users.id est un Integer, pas un UUID -- même
incompatibilité que celle déjà corrigée sur IncidentTicket.created_by.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mcp_call import MCPCall, MCPCallStatus


def log_mcp_call(
    db: Session,
    *,
    user_id: int,
    persona: str,
    tool_name: str,
    arguments: dict[str, Any],
    result: Any = None,
    status: MCPCallStatus = MCPCallStatus.SUCCESS,
    error_message: str | None = None,
    action_request_id: uuid.UUID | None = None,
    correlation_id: uuid.UUID | None = None,
) -> MCPCall:
    """
    Enregistre un appel d'outil MCP.

    Commite la session reçue : la trace doit survivre même si l'appelant
    échoue juste après (c'est précisément le cas qu'on veut pouvoir auditer).
    """
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
    db.commit()
    db.refresh(call)
    return call


def get_calls_for_correlation(db: Session, correlation_id: uuid.UUID) -> list[MCPCall]:
    """Tous les appels MCP liés à une même analyse d'incident (traçabilité RCA)."""
    statement = (
        select(MCPCall)
        .where(MCPCall.correlation_id == correlation_id)
        .order_by(MCPCall.created_at)
    )
    return list(db.execute(statement).scalars().all())
