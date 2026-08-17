import random


def get_cpu_usage() -> dict:
    return {
        "usage_percent": round(random.uniform(10, 95), 1),
        "top_process": random.choice(["nginx", "python3", "java", "mysqld", "backup_script.sh"]),
        "cores": 4,
    }