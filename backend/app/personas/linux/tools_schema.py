LINUX_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_cpu_usage",
            "description": "Obtenir l'usage CPU actuel du serveur (pourcentage, processus principal, nombre de coeurs)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ram_usage",
            "description": "Obtenir l'usage RAM actuel du serveur (total, utilise, pourcentage)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_disk_usage",
            "description": "Obtenir l'espace disque utilise sur le serveur (total, utilise, pourcentage, point de montage)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_services_status",
            "description": "Verifier le statut des services systeme critiques (nginx, postgresql, sshd, docker, cron)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_network",
            "description": "Verifier l'etat du reseau (latence, perte de paquets, statut de l'interface)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_incidents",
            "description": "Recupere la liste des incidents Linux recents enregistres en base de donnees (detectes automatiquement ou signales par un utilisateur).",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["open", "resolved"],
                        "description": "Filtrer par statut. Omettre pour tout recuperer.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Nombre maximum d'incidents a recuperer (defaut 10).",
                    },
                },
                "required": [],
            },
        },
    },
]