import random


def get_ram_usage() -> dict:
    total_gb = 16
    used_gb = round(random.uniform(4, 15), 1)
    return {
        "total_gb": total_gb,
        "used_gb": used_gb,
        "usage_percent": round((used_gb / total_gb) * 100, 1),
    }