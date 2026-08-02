from app.personas.linux.agent import linux_persona

prompt = linux_persona.build_prompt("Comment remplacer un disque défaillant sur TrueNAS ?")
print(prompt)