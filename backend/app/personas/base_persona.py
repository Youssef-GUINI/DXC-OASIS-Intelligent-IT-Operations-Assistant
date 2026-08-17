import json

from app.llm.groq_client import groq_client
from app.rag.query_pipeline import get_context_for_query


class BasePersona:
    name: str = "base"
    system_prompt: str = "Tu es un assistant technique."
    rag_collection: str | None = None
    mcp_client = None
    tools_schema: list | None = None
    db_tools: dict | None = None  # {"nom_outil": fonction(db, **kwargs)}

    def build_system_message(self, user_message: str) -> str:
        context = ""
        if self.rag_collection:
            try:
                context = get_context_for_query(self.rag_collection, user_message)
            except Exception:
                context = ""

        if context:
            return (
                f"{self.system_prompt}\n\n"
                f"Voici des extraits de documentation technique pertinents :\n"
                f"{context}\n\n"
                f"Utilise ce contexte quand il est pertinent, et utilise les "
                f"outils disponibles quand la question necessite des donnees "
                f"reelles du systeme ou de l'historique des incidents."
            )
        return self.system_prompt

    def handle_message(self, user_message: str, db=None) -> str:
        system_message = self.build_system_message(user_message)

        if not self.tools_schema:
            return groq_client.chat(user_message, system_prompt=system_message)

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

        for _ in range(10):
            message = groq_client.chat_with_tools(messages, self.tools_schema)

            if not message.tool_calls:
                return message.content

            messages.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [tc.model_dump() for tc in message.tool_calls],
                }
            )

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments or "{}")

                result = self._execute_tool(tool_name, tool_args, db)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )

        return "Impossible d'obtenir une reponse finale apres plusieurs appels d'outils."

    def _execute_tool(self, tool_name: str, tool_args: dict, db) -> dict:
        if self.db_tools and tool_name in self.db_tools:
            if db is None:
                return {"error": "Base de donnees non disponible pour cet outil"}
            try:
                return {"result": self.db_tools[tool_name](db, **tool_args)}
            except Exception as exc:
                return {"error": str(exc)}

        if self.mcp_client:
            try:
                return {"result": self.mcp_client.call(tool_name, tool_args)}
            except Exception as exc:
                return {"error": str(exc)}

        return {"error": f"Outil inconnu : {tool_name}"}