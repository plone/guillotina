from guillotina import configure


app_settings = {
    "mcp": {
        "enabled": True,
        "base_url": None,
        "auth": {
            "type": "basic",
            "username": "root",
            "password": None,
        },
        "description_extras": {},
        "extra_tools_module": None,
    },
    "commands": {
        "mcp-server": "guillotina.contrib.mcp.command.MCPServerCommand",
    },
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.mcp.permissions")
    configure.scan("guillotina.contrib.mcp.services")
