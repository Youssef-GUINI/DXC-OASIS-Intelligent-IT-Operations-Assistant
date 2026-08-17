from app.mcp.linux.tools import (
    cpu,
    ram,
    disk,
    services,
    network,
    incidents,
)
TOOLS = {
    "get_cpu_usage": cpu.get_cpu_usage,
    "get_ram_usage": ram.get_ram_usage,
    "get_disk_usage": disk.get_disk_usage,
    "get_services_status": services.get_services_status,
    "check_network": network.check_network,
    "get_incidents": incidents.get_incidents,
}


def handle_request(method: str, params: dict | None = None) -> dict:
    """
    Point d'entree du MCP Server. Recoit un nom de methode + parametres,
    execute l'outil correspondant, retourne le resultat.
    Format inspire de JSON-RPC : soit {"result": ...}, soit {"error": ...}.
    """
    if method not in TOOLS:
        return {"error": f"Outil inconnu : {method}"}

    func = TOOLS[method]
    params = params or {}
    try:
        result = func(**params)
        return {"result": result}
    except Exception as exc:
        return {"error": str(exc)}