from app.mcp.linux.server import handle_request


class LinuxMCPClient:
    def call(self, method: str, params: dict | None = None):
        response = handle_request(method, params)
        if "error" in response:
            raise RuntimeError(f"Linux MCP Server error: {response['error']}")
        return response["result"]


linux_mcp_client = LinuxMCPClient()