"""
Storage MCP Client — implémentation avec le SDK officiel `mcp` (v2.0.0).

Un seul sous-process pour toute la durée de vie de l'application FastAPI
(démarré dans le lifespan de main.py), réutilisé pour tous les appels de
tools plutôt que d'en relancer un par requête HTTP — coût de démarrage du
sous-process payé une seule fois.

Un asyncio.Lock sérialise les appels : la session MCP stdio n'est pas
conçue pour des appels concurrents simultanés sur la même session, donc
si deux requêtes /storage/chat arrivent en même temps, l'une attend que
l'autre ait fini son échange avec le sous-process avant de démarrer.
"""
import asyncio
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

# backend/app/mcp/storage/client.py -> on remonte de 3 niveaux pour
# retrouver backend/. On fixe explicitement le cwd du sous-process plutôt
# que de compter sur le cwd d'uvicorn au moment du lancement (qui dépend
# de l'endroit d'où on lance uvicorn/VSCode — source du bug "Connection
# closed" : le sous-process ne trouvait pas le package "app").
_BACKEND_DIR = Path(__file__).resolve().parents[3]

_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,  # garantit le même interpréteur/venv qu'uvicorn, pas un "python3" hypothétique dans le PATH
    args=["-m", "app.mcp.storage.tool_server"],
    cwd=str(_BACKEND_DIR),
)

# Mots-clés -> tool à appeler. Même logique de routage que la V1 in-process
# (pas de classifieur IA, cf. décision LLM Router étape 3).
_KEYWORD_ROUTES = [
    (("capacité", "capacite", "espace disque", "combien reste"), "get_capacity", {}),
    (("snapshot",), "list_snapshots", {"volume_id": "vol-prod-db01"}),
    (("sauvegarde", "backup"), "list_backups", {}),
    (("restaur",), "restore_from_backup", {"target": "vol-prod-db01", "backup_id": "snap-db01-0803"}),
    (("disaster", "sinistre", "failover", "bascul", "dr "), "get_dr_status", {}),
]
_CONFIRM_KEYWORDS = ("je confirme", "confirmé", "confirme la", "oui confirme")


class StorageMCPClient:
    def __init__(self):
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """À appeler une fois, au démarrage de FastAPI (lifespan)."""
        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(_SERVER_PARAMS))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

    async def stop(self) -> None:
        """À appeler à l'arrêt de FastAPI, pour fermer le sous-process proprement."""
        if self._stack is not None:
            await self._stack.aclose()
        self._session = None
        self._stack = None

    async def call_tool(self, tool_name: str, **kwargs) -> dict:
        if self._session is None:
            return {"error": "StorageMCPClient non démarré — vérifier le lifespan FastAPI"}

        async with self._lock:
            result = await self._session.call_tool(tool_name, kwargs)

        if result.is_error:
            return {"error": result.content[0].text if result.content else "Erreur MCP inconnue"}

        # Le SDK renvoie le retour du tool sous forme de TextContent JSON stringifié.
        import json
        return json.loads(result.content[0].text)

    async def detect_and_call(self, user_message: str) -> dict | None:
        """
        Détecte si le message utilisateur correspond à un besoin d'outil
        MCP et l'exécute si oui. Retourne None si aucun outil ne
        correspond.
        """
        message_lower = user_message.lower()

        for keywords, tool_name, default_params in _KEYWORD_ROUTES:
            if any(kw in message_lower for kw in keywords):
                params = dict(default_params)
                if tool_name in ("restore_from_backup", "initiate_failover"):
                    params["confirm"] = any(kw in message_lower for kw in _CONFIRM_KEYWORDS)

                result = await self.call_tool(tool_name, **params)
                return {"tool_name": tool_name, "params": params, "result": result}

        return None


storage_mcp_client = StorageMCPClient()