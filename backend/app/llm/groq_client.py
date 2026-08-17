"""Client Groq bas niveau, avec support natif du function/tool calling."""
from __future__ import annotations

from typing import Any
import logging
from groq import Groq

from app.core.config import settings

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self) -> None:
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = getattr(settings, "groq_model", "openai/gpt-oss-120b")

    def chat(self, prompt: str, system_prompt: str | None = None) -> str:
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat_with_tools(messages).content or ""

    def chat_with_tools(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> Any:
        """Retourne le message complet pour que le persona puisse rejouer les tool calls."""
        candidate_models = [self.model, "openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"]
        # deduplicate maintaining order
        candidate_models = list(dict.fromkeys(candidate_models))

        last_error = None
        for candidate in candidate_models:
            try:
                options: dict[str, Any] = {"model": candidate, "messages": messages, "temperature": 0.3}
                if tools:
                    options.update({"tools": tools, "tool_choice": "auto"})
                response = self.client.chat.completions.create(**options)
                self.model = candidate
                return response.choices[0].message
            except Exception as e:
                last_error = e
                logger.warning("Groq model %s error: %s. Trying candidate fallback...", candidate, e)
                continue

        if last_error:
            raise last_error


groq_client = GroqClient()

