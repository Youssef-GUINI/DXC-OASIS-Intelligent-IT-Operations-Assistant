import json
import uuid

from app.personas.storage.prompts import STORAGE_SYSTEM_PROMPT
from app.rag.retriever import retriever
from app.mcp.storage.client import storage_mcp_client
from app.llm.groq_client import groq_client
from app.mcp.storage.tools.health import get_storage_health
from app.models.incident_ticket import IncidentSeverity
from app.services.incident_service import estimate_severity

# Nombre max d'allers-retours LLM <-> tools avant d'arrêter la boucle,
# pour éviter un enchaînement infini si le modèle appelle des tools en
# boucle sans jamais conclure.
_MAX_TOOL_ROUNDS = 6

# Tools dont le paramètre confirm ne doit JAMAIS être décidé par le LLM
# lui-même — cf. commentaire dans la boucle d'exécution plus bas.
_DESTRUCTIVE_TOOLS = {"restore_from_backup", "initiate_failover"}
_CONFIRM_KEYWORDS = ("je confirme", "confirmé", "confirme la", "oui confirme", "oui, confirme")


class StoragePersona:
    """
    Persona spécialisé stockage/sauvegarde/reprise.

    Contrairement à la version précédente (prompt statique + détection
    par mots-clés), c'est ici le LLM lui-même qui décide, via le tool
    calling natif de l'API Groq, s'il a besoin d'appeler un ou plusieurs
    outils MCP, lesquels, et avec quels paramètres — avant de formuler sa
    réponse finale.
    """

    name = "storage_persona"
    system_prompt = STORAGE_SYSTEM_PROMPT
    rag_collection = "storage_kb"

    async def handle_message(self, user_message: str) -> str:
        context = retriever.retrieve(
            collection_name=self.rag_collection,
            question=user_message,
            n_results=3,
        )
        context_for_prompt = context or "Aucun extrait de documentation interne pertinent n'a été trouvé."

        tools = await storage_mcp_client.list_tools_for_llm()

        messages = [
            {
                "role": "system",
                "content": f"""{self.system_prompt}

Tu as accès à des outils MCP réels pour obtenir des données de stockage à jour (capacité disque, sauvegardes, snapshots, statut DR). Utilise-les dès que la question porte sur un état ou une donnée factuelle actuelle — n'invente jamais de chiffres.

Documentation interne pertinente (source RAG) :
{context_for_prompt}
""",
            },
            {"role": "user", "content": user_message},
        ]

        for _ in range(_MAX_TOOL_ROUNDS):
            assistant_message = groq_client.chat_with_tools(messages, tools=tools)

            if not assistant_message.tool_calls:
                # Le LLM a jugé ne pas avoir besoin (ou plus besoin) d'outil,
                # sa réponse est la réponse finale.
                return assistant_message.content

            # On rejoue le message assistant (avec ses tool_calls) dans
            # l'historique, requis par l'API pour la suite de l'échange.
            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in assistant_message.tool_calls
                ],
            })

            for tool_call in assistant_message.tool_calls:
                try:
                    args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                # Cas limite observé avec Groq : arguments="null" pour un tool
                # sans paramètre (au lieu de "{}") -> json.loads le convertit
                # en None, qui casse **args plus loin.
                if not isinstance(args, dict):
                    args = {}

                # GARDE-FOU DE SÉCURITÉ : pour les actions destructives, le LLM
                # ne décide JAMAIS lui-même de confirm=True — même s'il essaie.
                # On écrase systématiquement ce paramètre par une vérification
                # déterministe du message ORIGINAL de l'utilisateur pour ce tour
                # de conversation. Sans ça, rien n'empêche le modèle de
                # confirmer une restauration ou un failover de son propre chef
                # dès le premier appel (bug constaté en test réel).
                if tool_call.function.name in _DESTRUCTIVE_TOOLS:
                    args["confirm"] = any(kw in user_message.lower() for kw in _CONFIRM_KEYWORDS)

                result = await storage_mcp_client.call_tool(tool_call.function.name, **args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        # Boucle épuisée sans réponse finale texte : on force une dernière
        # réponse sans proposer de nouveaux tools, pour ne jamais renvoyer
        # une réponse vide à l'utilisateur.
        final = groq_client.chat_with_tools(messages, tools=None)
        return final.content or "Je n'ai pas pu obtenir de réponse définitive, réessaie ta question."


storage_persona = StoragePersona()
"""
À INTÉGRER dans app/personas/storage/agent.py (fichier existant).

analyze_incident() n'est PAS un tool exposé au LLM via tool calling : c'est
une méthode de StoragePersona appelée directement par la route API, qui
orchestre elle-même la séquence d'appels MCP (ordre garanti côté code),
puis délègue uniquement la rédaction du diagnostic à Groq.

Raison de ce choix (cf. décision validée) : pour un incident, on veut être
sûr que toutes les données nécessaires sont collectées, sans dépendre de la
décision du LLM d'appeler ou non tel ou tel tool.
"""



# NOTE: le logging des appels MCP (table mcp_calls) se fait UNIQUEMENT dans
# StorageMCPClient.call_tool() (cf. client_call_tool_patch.py), jamais ici,
# pour éviter un double enregistrement du même appel. analyze_incident se
# contente de passer correlation_id/user_id à travers chaque appel.

_RCA_SYSTEM_PROMPT = """Tu es un ingénieur SRE senior spécialisé en stockage et sauvegarde.
On te fournit des données brutes (statut des jobs de backup, logs, capacité disque,
réplication DR) ainsi que des extraits de runbooks internes.

Rédige une analyse de cause probable (Root Cause Analysis) structurée avec :
1. Diagnostic : ce qui s'est passé, factuel, basé uniquement sur les données fournies
2. Cause probable : la cause la plus vraisemblable, justifiée par les données
3. Impact : conséquence concrète pour l'exploitation
4. Recommandations : liste d'actions concrètes, numérotées, sans exécuter
   d'action destructive toi-même — tu proposes, l'ingénieur décide.

Ne jamais inventer de données non présentes dans le contexte fourni.
Si les données sont insuffisantes pour conclure, dis-le explicitement plutôt
que de spéculer."""


class IncidentAnalysisMixin:
    """À fusionner dans la classe StoragePersona existante."""

    async def analyze_incident(self, user_message: str, *, user_id, db) -> dict:
        correlation_id = uuid.uuid4()

        # 1. Séquence d'appels MCP forcée côté code (pas laissée au LLM).
        # db est passé au client pour que call_tool() logue chaque appel
        # dans mcp_calls avec le bon correlation_id (cf. client_call_tool_patch.py)
        job_status = await self.storage_mcp_client.call_tool(
            "get_backup_job_status", db=db, user_id=user_id, correlation_id=correlation_id,
        )

        # Cible les logs sur le job en échec le plus récent, s'il y en a un
        failed_jobs = [j for j in job_status.get("jobs", []) if j.get("status") == "failed"]
        logs = {}
        if failed_jobs:
            logs = await self.storage_mcp_client.call_tool(
                "get_backup_logs", job_id=failed_jobs[0]["job_id"],
                db=db, user_id=user_id, correlation_id=correlation_id,
            )

        capacity = await self.storage_mcp_client.call_tool(
            "get_capacity", db=db, user_id=user_id, correlation_id=correlation_id,
        )
        replication = await self.storage_mcp_client.call_tool(
            "get_replication_status", db=db, user_id=user_id, correlation_id=correlation_id,
        )

        # Vue agrégée pour le calcul de sévérité (règles déterministes)
        health = get_storage_health()
        severity = estimate_severity(health)

        raw_data = {
            "job_status": job_status,
            "logs": logs,
            "capacity": capacity,
            "replication": replication,
        }

        # 2. Contexte RAG (runbooks)
        rag_context = await self.retrieve_rag_context(user_message)

        # 3. Groq rédige diagnostic/RCA/recommandations à partir des données réelles
        prompt = (
            f"Question de l'ingénieur : {user_message}\n\n"
            f"Données MCP collectées :\n{raw_data}\n\n"
            f"Extraits de runbooks pertinents :\n{rag_context}\n\n"
            f"Sévérité déjà calculée par le système : {severity.value}"
        )
        analysis_text = await self.groq_client.chat(prompt, system_prompt=_RCA_SYSTEM_PROMPT)

        return {
            "correlation_id": correlation_id,
            "severity": severity,
            "raw_mcp_data": raw_data,
            "analysis_text": analysis_text,
            # ticket suggéré si sévérité haute — mais PAS créé automatiquement
            "ticket_suggested": severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH),
        }