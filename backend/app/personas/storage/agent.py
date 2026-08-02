from app.personas.base_persona import BasePersona
from app.personas.storage.prompts import STORAGE_SYSTEM_PROMPT
from app.rag.retriever import retriever


class StoragePersona(BasePersona):
    """Persona specialise dans le stockage, les sauvegardes et la reprise."""

    name = "storage_persona"
    system_prompt = STORAGE_SYSTEM_PROMPT
    rag_collection = "storage_kb"

    def build_prompt(self, user_message: str) -> str:
        context = retriever.retrieve(
            collection_name=self.rag_collection,
            question=user_message,
            n_results=3,
        )
        context_for_prompt = context or (
            "Aucun extrait de documentation interne pertinent n'a été trouvé."
        )

        return f"""
{self.system_prompt}

==========================================
Documentation interne Storage (source RAG)
==========================================

Les extraits suivants proviennent de la base documentaire interne.
Ils constituent la source principale de la réponse.


{context_for_prompt}

==============================
Question utilisateur
==============================

{user_message}

Consignes :

- Base ta réponse en priorité sur les extraits de documentation interne fournis.
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
