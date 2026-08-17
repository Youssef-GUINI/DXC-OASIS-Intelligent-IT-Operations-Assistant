"""Client MCP Storage persistant et point unique d'audit des appels."""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from sqlalchemy.orm import Session

from app.models.mcp_call import MCPCallStatus
from app.services.mcp_audit import log_mcp_call

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parents[3]
_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable, args=["-m", "app.mcp.storage.tool_server"], cwd=str(_BACKEND_DIR)
)


class StorageMCPClient:
    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "StorageMCPClient":
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.stop()

    async def start(self) -> None:
        if self._session is not None:
            return
        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(_SERVER_PARAMS))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

    async def stop(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._session = None
        self._stack = None

    def _require_session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("Storage MCP indisponible : verifier le lifespan FastAPI.")
        return self._session

    async def list_tools_for_llm(self) -> list[dict[str, Any]]:
        response = await self._require_session().list_tools()
        return [
            {"type": "function", "function": {
                "name": tool.name,
                "description": tool.description or tool.name,
                "parameters": getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", {}),
            }}
            for tool in response.tools
        ]

    async def call_tool(
        self,
        tool_name: str,
        *,
        # Session synchrone (sqlalchemy.orm.Session) et users.id -> int.
        # Fournir les deux active l'audit dans mcp_calls ; les omettre laisse
        # l'appel non tracé, ce qui ne doit rester vrai que pour les tests.
        db: Session | None = None,
        user_id: int | None = None,
        correlation_id: uuid.UUID | None = None,
        action_request_id: uuid.UUID | None = None,
        **arguments: Any,
    ) -> dict[str, Any]:
        status = MCPCallStatus.SUCCESS
        result: dict[str, Any] | None = None
        error_message: str | None = None
        try:
            async with self._lock:
                raw = await self._require_session().call_tool(tool_name, arguments)
            if getattr(raw, "isError", False) or getattr(raw, "is_error", False):
                raise RuntimeError("; ".join(
                    item.text for item in raw.content if hasattr(item, "text")
                ) or "Erreur MCP inconnue")
            text = "\n".join(item.text for item in raw.content if hasattr(item, "text"))
            result = json.loads(text) if text else {"result": raw.model_dump(mode="json")}
        except Exception as error:
            status = MCPCallStatus.FAILED
            error_message = str(error)

        if db is not None and user_id is not None:
            # log_mcp_call est synchrone : pas de `await` (cf. mcp_audit.py).
            # Un échec d'audit ne doit pas masquer le résultat de l'outil.
            try:
                log_mcp_call(
                    db, user_id=user_id, persona="storage", tool_name=tool_name,
                    arguments=arguments, result=result, status=status,
                    error_message=error_message, correlation_id=correlation_id,
                    action_request_id=action_request_id,
                )
            except Exception:  # noqa: BLE001
                logger.exception("Echec de l'audit MCP pour l'outil %s", tool_name)
        if status == MCPCallStatus.FAILED:
            raise RuntimeError(error_message or "Erreur MCP inconnue")
        return result or {}


storage_mcp_client = StorageMCPClient()
