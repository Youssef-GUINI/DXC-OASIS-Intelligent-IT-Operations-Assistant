from app.personas.linux.agent import linux_persona

response = linux_persona.handle_message("Quel est l'etat actuel du CPU et de la RAM sur le serveur ?")
print(response)