from app.orchestrator.llm_router import route, TaskComplexity


class BasePersona:
    """
    Comportement commun a tous les Personas.
    Chaque Persona specialise ajoute son propre system_prompt et,
    plus tard, son propre RAG et ses propres outils MCP.
    """

    name: str = "base"
    system_prompt: str = "Tu es un assistant technique."

    def build_prompt(self, user_message: str) -> str:
        return f"{self.system_prompt}\n\nQuestion de l'utilisateur : {user_message}"

    def handle_message(self, user_message: str, complexity: TaskComplexity = TaskComplexity.SIMPLE) -> str:
        full_prompt = self.build_prompt(user_message)
        return route(full_prompt, complexity=complexity)