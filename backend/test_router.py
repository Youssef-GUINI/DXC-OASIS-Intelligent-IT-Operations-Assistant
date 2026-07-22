from app.orchestrator.llm_router import route

response = route("Explique en une phrase ce qu'est un incident IT.")
print(response)