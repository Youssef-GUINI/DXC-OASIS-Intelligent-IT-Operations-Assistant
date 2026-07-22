from enum import Enum

from app.llm.groq_client import groq_client


class TaskComplexity(str, Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"


def route(prompt: str, complexity: TaskComplexity = TaskComplexity.SIMPLE) -> str:
    """
    Decide quel LLM utiliser et retourne la reponse.
    Regle V1 (simple, pas de classifieur IA - cf architecture figee section 8) :
      - SIMPLE  -> Groq (Llama 3.1/3.3)
      - COMPLEX -> Claude (a brancher plus tard)
    """
    if complexity == TaskComplexity.COMPLEX:
        # TODO: brancher app.llm.anthropic_client une fois la cle Claude prete
        raise NotImplementedError("Claude pas encore branche - utilise TaskComplexity.SIMPLE pour l'instant")

    return groq_client.chat(prompt)