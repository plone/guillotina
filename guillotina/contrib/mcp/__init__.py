from guillotina import configure


app_settings = {
    "mcp": {
        "enabled": True,
        "server_name": "guillotina-mcp",
        "default_child_limit": 50,
    },
    "load_utilities": {
        "mcp_tool_registry": {
            "provides": "guillotina.contrib.mcp.interfaces.IMCPToolRegistry",
            "factory": "guillotina.contrib.mcp.backend.MCPToolRegistry",
            "settings": {},
        }
    },
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.mcp.install")
    configure.scan("guillotina.contrib.mcp.permissions")
    configure.scan("guillotina.contrib.mcp.services")
    configure.scan("guillotina.contrib.mcp.subscribers")
