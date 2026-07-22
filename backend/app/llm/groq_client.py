from groq import Groq

from app.core.config import settings


class GroqClient:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)   
    def chat(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content


groq_client = GroqClient()