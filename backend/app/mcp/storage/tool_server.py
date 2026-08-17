"""Serveur MCP Storage lance en sous-process via le transport stdio."""
from mcp.server.mcpserver import MCPServer

from app.mcp.storage.server import TOOL_REGISTRY

mcp = MCPServer("oasis-storage-mcp")
for _tool in TOOL_REGISTRY.values():
    mcp.tool()(_tool)


if __name__ == "__main__":
    mcp.run(transport="stdio")
