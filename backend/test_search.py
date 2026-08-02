from app.personas.storage.agent import storage_persona

prompt = storage_persona.build_prompt("Comment remplacer un disque défaillant sur TrueNAS ?")
print(prompt)