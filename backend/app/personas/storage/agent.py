"""Persona Storage : RAG, tool calling Groq et garde-fou d'actions."""
from __future__ import annotations

import json
import logging
import uuid

from app.llm.groq_client import groq_client
from app.mcp.storage.client import StorageMCPClient
from app.mcp.storage.server import DESTRUCTIVE_TOOLS
from app.personas.storage.incident_rules import evaluate_tool_result
from app.personas.storage.prompts import STORAGE_SYSTEM_PROMPT
from app.rag.retriever import retriever
from app.services import incident_service

# session.py confirme : SessionLocal est un sessionmaker SYNC classique
# (sqlalchemy.orm.sessionmaker), pas un async_sessionmaker.
from app.database.session import SessionLocal

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 6


class StoragePersona:
    name = "storage_persona"
    rag_collection = "storage_kb"

    async def handle_message(self, user_message: str, created_by: int | None = None) -> str:
        context = retriever.retrieve(
            collection_name=self.rag_collection, question=user_message, n_results=3
        )
        messages: list[dict] = [
            {"role": "system", "content": f"""{STORAGE_SYSTEM_PROMPT}

Utilise MCP uniquement pour les informations de stockage actuelles. Les outils
de restauration et de failover ne sont jamais executables dans le chat : une
action sensible doit etre proposee au frontend puis confirmee par son endpoint
authentifie dedie. Documentation RAG :
{context or 'Aucune documentation interne pertinente trouvee.'}"""},
            {"role": "user", "content": user_message},
        ]

        detected_tickets: list[dict] = []
        final_text: str | None = None
        correlation_id = uuid.uuid4()

        # Session dédiée à l'audit des appels MCP, ouverte pour toute la boucle
        # d'outils : tous les appels d'une même conversation partagent ainsi le
        # même correlation_id. Sans created_by on ne sait pas à qui imputer
        # l'appel -- on n'audite pas, plutôt que d'inventer un utilisateur.
        audit_db = SessionLocal() if created_by is not None else None

        try:
            async with StorageMCPClient() as mcp:
                tools = await mcp.list_tools_for_llm()
                for _ in range(_MAX_TOOL_ROUNDS):
                    reply = groq_client.chat_with_tools(messages, tools)
                    if not reply.tool_calls:
                        final_text = reply.content or "Je n'ai pas pu produire de reponse."
                        break

                    messages.append({
                        "role": "assistant", "content": reply.content or "",
                        "tool_calls": [{
                            "id": call.id, "type": "function",
                            "function": {
                                "name": call.function.name, "arguments": call.function.arguments,
                            },
                        } for call in reply.tool_calls],
                    })

                    for call in reply.tool_calls:
                        name = call.function.name
                        try:
                            arguments = json.loads(call.function.arguments or "{}")
                            if not isinstance(arguments, dict):
                                arguments = {}
                        except json.JSONDecodeError:
                            arguments = {}

                        if name in DESTRUCTIVE_TOOLS:
                            result = {
                                "status": "denied", "reason": "confirmation_required",
                                "message": "Action sensible non executee depuis le chat. "
                                           "Utilisez le circuit /storage/actions authentifie.",
                            }
                        else:
                            try:
                                result = await mcp.call_tool(
                                    name,
                                    db=audit_db,
                                    user_id=created_by,
                                    correlation_id=correlation_id,
                                    **arguments,
                                )
                            except RuntimeError as error:
                                result = {"status": "error", "message": str(error)}

                        detected_tickets.extend(evaluate_tool_result(name, result))

                        messages.append({
                            "role": "tool", "tool_call_id": call.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
        finally:
            if audit_db is not None:
                audit_db.close()

        if final_text is None:
            final = groq_client.chat_with_tools(messages)
            final_text = final.content or "Limite de collecte MCP atteinte; reessayez avec une question plus ciblee."

        # --- Creation automatique des tickets detectes -----------------------
        # SessionLocal est sync -> pas de "async with", pas de "await" sur
        # les appels incident_service.
        if detected_tickets and created_by is not None:
            try:
                with SessionLocal() as db:
                    for ticket_data in detected_tickets:
                        incident_service.create_ticket_from_diagnosis(
                            db,
                            created_by=created_by,
                            correlation_id=correlation_id,
                            **ticket_data,
                        )
            except Exception:
                logger.exception("Echec de la creation automatique d'un ticket d'incident")
        elif detected_tickets and created_by is None:
            logger.warning(
                "Anomalie(s) detectee(s) mais aucun created_by fourni -- "
                "ticket(s) non cree(s): %s",
                [t["title"] for t in detected_tickets],
            )

        return final_text


storage_persona = StoragePersona()