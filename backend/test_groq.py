from app.llm.groq_client import groq_client

response = groq_client.chat(
    "Say hello in one sentence."
)

print(response)