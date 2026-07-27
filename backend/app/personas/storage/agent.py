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

==============================
Documentation interne Storage
==============================

{context_for_prompt}

==============================
Question utilisateur
==============================

{user_message}

Consignes :

- Utilise en priorité la documentation interne lorsqu'elle est pertinente.
- Si aucun extrait n'est fourni, dis-le explicitement et n'invente ni titre,
  ni contenu de documentation interne.
- Si elle ne suffit pas, indique clairement ce qui relève de tes recommandations.
- N'affirme jamais qu'une sauvegarde, une restauration ou un snapshot a été exécuté
  sans résultat explicite d'un outil MCP.
- Donne une réponse claire, technique et structurée.
""".strip()


storage_persona = StoragePersona()
