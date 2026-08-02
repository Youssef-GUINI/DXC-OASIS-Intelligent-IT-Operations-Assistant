from app.personas.storage.agent import storage_persona

response = storage_persona.handle_message(
    "Comment remplacer un disque défaillant sur TrueNAS ?"
)
print(response)