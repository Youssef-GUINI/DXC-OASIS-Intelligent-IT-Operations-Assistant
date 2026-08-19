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
            model=settings.groq_model,
            messages=messages,
            temperature=0,
            max_completion_tokens=settings.groq_max_tokens,
        )
        return response.choices[0].message.content or ""

    def chat_with_tools(self, messages: list, tools: list, tool_choice: str = "auto"):
        response = self.client.chat.completions.create(
            model=settings.groq_tool_model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=0,
            max_completion_tokens=settings.groq_max_tokens,
        )
        return response.choices[0].message


groq_client = GroqClient()
