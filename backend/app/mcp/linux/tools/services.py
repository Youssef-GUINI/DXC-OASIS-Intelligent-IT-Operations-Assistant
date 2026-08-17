import random


def get_services_status() -> dict:
    services = ["nginx", "postgresql", "sshd", "docker", "cron"]
    return {
        s: random.choice(["active", "active", "active", "failed"])  # failed rare
        for s in services
    }