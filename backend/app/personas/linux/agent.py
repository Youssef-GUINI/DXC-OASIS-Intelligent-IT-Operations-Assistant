from app.personas.base_persona import BasePersona
from app.rag.retriever import retriever


class LinuxPersona(BasePersona):
    name = "linux_persona"

    system_prompt = (
        "Tu es un ingénieur système Linux expert spécialisé dans le "
        "troubleshooting des incidents Linux, CPU, RAM, disque, "
        "services systemd et réseau."
    )

    def build_prompt(self, user_message: str) -> str:

        context = retriever.retrieve(
            collection_name="linux_kb",
            question=user_message,
            n_results=3,
        )

        return f"""
{self.system_prompt}

==============================
Documentation interne DXC
==============================

{context}

==============================
Question utilisateur
==============================

{user_message}

Consignes :

- Utilise en priorité la documentation interne.
- Si elle ne contient pas la réponse, complète avec tes connaissances Linux.
- Donne une réponse claire, technique et structurée.
"""


linux_persona = LinuxPersona()