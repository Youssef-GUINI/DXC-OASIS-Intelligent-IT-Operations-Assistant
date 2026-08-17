import random


def get_disk_usage() -> dict:
    total_gb = 500
    used_gb = round(random.uniform(100, 480), 1)
    return {
        "total_gb": total_gb,
        "used_gb": used_gb,
        "usage_percent": round((used_gb / total_gb) * 100, 1),
        "mount_point": "/",
    }