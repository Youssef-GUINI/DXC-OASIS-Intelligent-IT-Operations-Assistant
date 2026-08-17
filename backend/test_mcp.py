from app.mcp.linux.client import linux_mcp_client

print(linux_mcp_client.call("get_cpu_usage"))
print(linux_mcp_client.call("get_ram_usage"))
print(linux_mcp_client.call("get_disk_usage"))
print(linux_mcp_client.call("get_services_status"))
print(linux_mcp_client.call("check_network"))