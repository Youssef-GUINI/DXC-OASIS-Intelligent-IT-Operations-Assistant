from groq import Groq

from app.core.config import settings


class GroqClient:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)

    def chat(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
        )

        return response.choices[0].message.content

    def chat_with_tools(self, messages: list[dict], tools: list[dict] | None = None):
        """
        Version bas niveau qui retourne l'objet message complet (pas juste
        le texte), pour permettre au caller d'inspecter message.tool_calls
        et de gérer lui-même la boucle d'exécution des tools.

        Important : quand tools est None/vide, on OMET complètement les
        paramètres tools et tool_choice de l'appel plutôt que de les passer
        explicitement à None — l'API Groq rejette un tool_choice=null
        explicite (400 Bad Request), elle attend soit une des 3 valeurs
        ["none", "auto", "required"], soit l'absence totale du champ.
        """
        kwargs = {}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            **kwargs,
        )
        return response.choices[0].message


groq_client = GroqClient()