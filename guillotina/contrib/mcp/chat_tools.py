from guillotina.contrib.mcp.tools import _get_description_extras
from guillotina.contrib.mcp.tools import TOOL_DESCRIPTIONS


def get_chat_tools():
    """Return MCP tool definitions in the format expected by LiteLLM/chat completion APIs (all providers)."""
    extras = _get_description_extras()
    descriptions = {
        name: (TOOL_DESCRIPTIONS[name] + " " + (extras.get(name) or "")).strip() for name in TOOL_DESCRIPTIONS
    }
    return [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": descriptions["search"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "container_path": {
                            "type": "string",
                            "description": "Optional path relative to container.",
                        },
                        "query": {
                            "type": "object",
                            "description": "Search query: type_name, term, _size, _from, _sort_asc, _sort_des, field filters.",  # noqa: E501
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "count",
                "description": descriptions["count"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "container_path": {
                            "type": "string",
                            "description": "Optional path relative to container.",
                        },
                        "query": {
                            "type": "object",
                            "description": "Count query: type_name, term, field filters (no _size/_from/_sort).",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_content",
                "description": descriptions["get_content"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path relative to container."},
                        "uid": {"type": "string", "description": "Resource UID."},
                        "container_path": {
                            "type": "string",
                            "description": "Optional path relative to container.",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_children",
                "description": descriptions["list_children"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path relative to container."},
                        "from_index": {
                            "type": "integer",
                            "description": "Offset (maps to _from).",
                            "default": 0,
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Page size (maps to _size).",
                            "default": 20,
                        },
                        "container_path": {
                            "type": "string",
                            "description": "Optional path relative to container.",
                        },
                    },
                },
            },
        },
    ]
