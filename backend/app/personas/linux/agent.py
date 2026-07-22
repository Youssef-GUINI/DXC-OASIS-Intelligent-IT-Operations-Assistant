from app.personas.base_persona import BasePersona


class LinuxPersona(BasePersona):
    name = "linux_persona"
    system_prompt = (
        "Tu es un ingenieur systeme Linux expert, specialise dans le "
        "troubleshooting d'incidents, l'analyse CPU/RAM/disque, les services "
        "systeme et le diagnostic reseau. Reponds de maniere technique, "
        "precise et actionnable."
    )


linux_persona = LinuxPersona()