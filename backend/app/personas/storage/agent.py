from app.personas.base_persona import BasePersona
from app.personas.storage.prompts import STORAGE_SYSTEM_PROMPT
from app.rag.retriever import retriever
from app.mcp.storage.client import storage_mcp_client


class StoragePersona(BasePersona):
    """Persona specialise dans le stockage, les sauvegardes et la reprise."""

    name = "storage_persona"
    system_prompt = STORAGE_SYSTEM_PROMPT
    rag_collection = "storage_kb"

    async def build_prompt(self, user_message: str) -> str:
        context = retriever.retrieve(
            collection_name=self.rag_collection,
            question=user_message,
            n_results=3,
        )
        context_for_prompt = context or (
            "Aucun extrait de documentation interne pertinent n'a été trouvé."
        )

        mcp_call = await storage_mcp_client.detect_and_call(user_message)
        if mcp_call:
            mcp_section = f"""
==========================================
Résultat d'outil MCP (donnée réelle, pas une supposition)
==========================================

Outil appelé : {mcp_call['tool_name']}
Résultat : {mcp_call['result']}
"""
        else:
            mcp_section = """
==========================================
Résultat d'outil MCP
==========================================

Aucun outil MCP n'a été appelé pour cette question.
"""

        return f"""
{self.system_prompt}

==========================================
Documentation interne Storage (source RAG)
==========================================

Les extraits suivants proviennent de la base documentaire interne.
Ils constituent la source principale de la réponse.


{context_for_prompt}
{mcp_section}
==============================
Question utilisateur
==============================

{user_message}

Consignes :

- Base ta réponse en priorité sur les extraits de documentation interne fournis.
- Si un résultat d'outil MCP est présent ci-dessus, base tes affirmations factuelles
  (capacité, statut de sauvegarde, statut DR, etc.) sur ce résultat en priorité,
  et cite les valeurs exactes qu'il contient.
- Si le résultat d'outil MCP demande une confirmation (action destructive), explique
  clairement le risque à l'utilisateur et demande sa confirmation explicite avant
  de considérer l'action comme faisable.
- Considère qu'un extrait est pertinent même s'il ne correspond pas mot pour mot
  à la question, dès lors qu'il traite du même sujet.
- Lorsque la documentation décrit une procédure, restitue-la en suivant l'ordre des étapes de la documentation.
- Reprends les noms exacts des menus, boutons et options (par exemple : View VDEVs, Offline, Replace, Force) sans les reformuler.
- N'invente pas d'étapes supplémentaires qui ne figurent pas dans les extraits fournis.
- Si la documentation ne répond que partiellement à la question, complète avec tes
  connaissances générales en indiquant clairement quelles informations proviennent
  de la documentation et lesquelles sont des recommandations générales.
- Si aucun extrait pertinent n'est fourni, indique-le explicitement.
- N'affirme jamais qu'une sauvegarde, une restauration ou un snapshot a été exécuté
  sans résultat explicite d'un outil MCP.
- Donne une réponse claire, technique et structurée.
""".strip()


storage_persona = StoragePersona()