import random


def check_network() -> dict:
    return {
        "latency_ms": round(random.uniform(1, 50), 1),
        "packet_loss_percent": round(random.uniform(0, 2), 2),
        "interface_status": "up",
    }