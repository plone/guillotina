from guillotina import configure


app_settings = {
    "mcp": {
        "enabled": True,
        "description_extras": {},
        "extra_tools_module": None,
        "token_max_duration_days": 90,
        "token_allowed_durations": None,
        "chat_enabled": True,
        "chat_model": None,
    },
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.mcp.permissions")
    configure.scan("guillotina.contrib.mcp.services")
    configure.scan("guillotina.contrib.mcp.chat")
