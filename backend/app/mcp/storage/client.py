"""
Storage MCP Client — SDK officiel `mcp` (v2.0.0), sous-process persistant.

Le routage par mots-clés (V2 précédente) est supprimé : c'est maintenant
le LLM lui-même qui décide, via le tool calling natif (function calling),
quel(s) outil(s) MCP appeler et avec quels paramètres — cf.
StoragePersona pour la boucle d'exécution.
"""
import asyncio
import sys
from contextlib import AsyncExitStack
from pathlib import Path
import uuid
from typing import Any

from app.models.mcp_call import MCPCallStatus
from app.services.mcp_audit import log_mcp_call

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

_BACKEND_DIR = Path(__file__).resolve().parents[3]

_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "app.mcp.storage.tool_server"],
    cwd=str(_BACKEND_DIR),
)


class StorageMCPClient:
    def __init__(self):
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(_SERVER_PARAMS))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

    async def stop(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._session = None
        self._stack = None

    async def list_tools_for_llm(self) -> list[dict]:
        """
        Récupère le catalogue de tools exposé par le MCP Server et le
        convertit au format attendu par l'API tool calling de Groq/OpenAI
        (le schéma JSON de chaque tool est déjà généré automatiquement par
        le SDK MCP depuis les type hints des fonctions Python — pas besoin
        de le réécrire à la main).
        """
        if self._session is None:
            return []

        tools_result = await self._session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools_result.tools
        ]

    async def call_tool(self, tool_name: str, **kwargs) -> dict:
        if self._session is None:
            return {"error": "StorageMCPClient non démarré — vérifier le lifespan FastAPI"}

        async with self._lock:
            result = await self._session.call_tool(tool_name, kwargs)

        if result.is_error:
            return {"error": result.content[0].text if result.content else "Erreur MCP inconnue"}

        import json
        return json.loads(result.content[0].text)


storage_mcp_client = StorageMCPClient()
"""
À INTÉGRER dans app/mcp/storage/client.py — remplace la méthode call_tool
existante de StorageMCPClient.

Point unique de logging : TOUT appel MCP passe par ici, que ce soit via la
boucle de tool calling classique (agent.py) ou via analyze_incident.
db/user_id/correlation_id sont optionnels pour ne pas casser les appels
existants qui ne les fournissent pas encore (migration progressive) — mais
à terme il faudrait les rendre obligatoires pour garantir l'audit complet.
"""




class StorageMCPClient:
    # ... (start(), stop(), list_tools_for_llm() inchangés) ...

    async def call_tool(
        self,
        tool_name: str,
        *,
        db=None,
        user_id: uuid.UUID | None = None,
        correlation_id: uuid.UUID | None = None,
        action_request_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict:
        async with self._lock:
            status = MCPCallStatus.SUCCESS
            error_message = None
            result: dict = {}
            try:
                raw = await self._session.call_tool(tool_name, kwargs)
                result = raw  # adapter selon le format exact retourné par ClientSession
            except Exception as e:
                status = MCPCallStatus.FAILED
                error_message = str(e)

        if db is not None and user_id is not None:
            await log_mcp_call(
                db,
                user_id=user_id,
                persona="storage",
                tool_name=tool_name,
                arguments=kwargs,
                result=result,
                status=status,
                error_message=error_message,
                correlation_id=correlation_id,
                action_request_id=action_request_id,
            )

        if status == MCPCallStatus.FAILED:
            raise RuntimeError(error_message)

        return result