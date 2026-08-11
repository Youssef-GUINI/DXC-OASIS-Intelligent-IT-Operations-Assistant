from app.orchestrator.llm_router import route, TaskComplexity


class BasePersona:
    """
    Comportement commun a tous les Personas.
    Chaque Persona specialise ajoute son propre system_prompt et,
    plus tard, son propre RAG et ses propres outils MCP.

    build_prompt et handle_message sont async : le Storage Persona doit
    pouvoir await un appel au sous-process MCP (I/O stdio) pendant la
    construction du prompt.
    """

    name: str = "base"
    system_prompt: str = "Tu es un assistant technique."

    async def build_prompt(self, user_message: str) -> str:
        return f"{self.system_prompt}\n\nQuestion de l'utilisateur : {user_message}"

    async def handle_message(self, user_message: str, complexity: TaskComplexity = TaskComplexity.SIMPLE) -> str:
        full_prompt = await self.build_prompt(user_message)
        # route() reste synchrone (appel HTTP bloquant vers Groq/Claude) :
        # acceptable pour la V1, à déplacer dans un threadpool si la charge
        # devient un problème réel.
        return route(full_prompt, complexity=complexity)