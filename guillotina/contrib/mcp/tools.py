from guillotina._settings import app_settings
from guillotina.contrib.mcp.backend import get_mcp_context
from guillotina.contrib.mcp.interfaces import IMCPDescriptionExtras

import typing


TOOL_DESCRIPTIONS = {
    "search": (
        "Search the catalog. container_path is optional (default: current context). "
        "query keys follow Guillotina @search: type_name, term, _size, _from, _sort_asc "
        "(field name for ascending), _sort_des (field name for descending), _metadata, "
        "_metadata_not; field filters: field__eq, field__not, field__gt, field__gte, "
        "field__lt, field__lte, field__in. E.g. creators__in to filter by creator."
    ),
    "count": (
        "Count catalog results. container_path is optional. query uses same keys as search: "
        "type_name, term, field__eq, field__gt, etc. (no _size/_from/_sort_asc/_sort_des)."
    ),
    "get_content": (
        "Get a resource by path (relative to container) or by UID. "
        "container_path is optional for in-process."
    ),
    "list_children": (
        "List direct children of a container. path: relative path to container. "
        "from_index: offset (maps to _from). page_size: page size (maps to _size). "
        "container_path is optional for in-process."
    ),
}

CHAT_PARAM_SCHEMAS = {
    "search": {
        "properties": {
            "container_path": {"type": "string", "description": "Optional path relative to container."},
            "query": {
                "type": "object",
                "description": "Search query: type_name, term, _size, _from, _sort_asc, _sort_des, field filters.",
            },
        },
    },
    "count": {
        "properties": {
            "container_path": {"type": "string", "description": "Optional path relative to container."},
            "query": {
                "type": "object",
                "description": "Count query: type_name, term, field filters (no _size/_from/_sort).",
            },
        },
    },
    "get_content": {
        "properties": {
            "path": {"type": "string", "description": "Path relative to container."},
            "uid": {"type": "string", "description": "Resource UID."},
            "container_path": {"type": "string", "description": "Optional path relative to container."},
        },
    },
    "list_children": {
        "properties": {
            "path": {"type": "string", "description": "Path relative to container."},
            "from_index": {"type": "integer", "description": "Offset (maps to _from).", "default": 0},
            "page_size": {"type": "integer", "description": "Page size (maps to _size).", "default": 20},
            "container_path": {"type": "string", "description": "Optional path relative to container."},
        },
    },
}


def _get_description_extras():
    from guillotina.component import query_utility

    extras = dict(app_settings.get("mcp", {}).get("description_extras") or {})
    util = query_utility(IMCPDescriptionExtras)
    if util is not None:
        for k, v in (util() or {}).items():
            extras[k] = (extras.get(k) or "") + (" " + v if v else "")
    return extras


def register_tools(mcp_server, backend):
    async def _context_for_path(container_path: typing.Optional[str]):
        ctx = get_mcp_context()
        if ctx is None:
            return None
        if container_path:
            from guillotina.utils import navigate_to

            try:
                return await navigate_to(ctx, "/" + container_path.strip("/"))
            except KeyError:
                return None
        return ctx

    extras = _get_description_extras()

    @mcp_server.tool(description=(TOOL_DESCRIPTIONS["search"] + " " + (extras.get("search") or "")).strip())
    async def search(
        container_path: typing.Optional[str] = None,
        query: typing.Optional[typing.Dict[str, str]] = None,
    ) -> dict:
        context = await _context_for_path(container_path)
        if context is None:
            return {"items": [], "items_total": 0}
        q = query or {}
        return await backend.search(context, q)

    @mcp_server.tool(description=(TOOL_DESCRIPTIONS["count"] + " " + (extras.get("count") or "")).strip())
    async def count(
        container_path: typing.Optional[str] = None,
        query: typing.Optional[typing.Dict[str, str]] = None,
    ):
        context = await _context_for_path(container_path)
        if context is None:
            return 0
        q = query or {}
        return await backend.count(context, q)

    @mcp_server.tool(
        description=(TOOL_DESCRIPTIONS["get_content"] + " " + (extras.get("get_content") or "")).strip()
    )
    async def get_content(
        path: typing.Optional[str] = None,
        uid: typing.Optional[str] = None,
        container_path: typing.Optional[str] = None,
    ) -> dict:
        context = await _context_for_path(container_path)
        if context is None:
            return {}
        return await backend.get_content(context, path, uid)

    @mcp_server.tool(
        description=(TOOL_DESCRIPTIONS["list_children"] + " " + (extras.get("list_children") or "")).strip()
    )
    async def list_children(
        path: str = "",
        from_index: int = 0,
        page_size: int = 20,
        container_path: typing.Optional[str] = None,
    ) -> dict:
        context = await _context_for_path(container_path)
        if context is None:
            return {"items": [], "items_total": 0}
        return await backend.list_children(context, path or "", from_index, page_size)


def get_chat_tools():
    """Return built-in tool definitions in the format expected by LiteLLM for @chat (all providers)."""
    extras = _get_description_extras()
    descriptions = {
        name: (TOOL_DESCRIPTIONS[name] + " " + (extras.get(name) or "")).strip() for name in TOOL_DESCRIPTIONS
    }
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": descriptions[name],
                "parameters": {"type": "object", **CHAT_PARAM_SCHEMAS[name]},
            },
        }
        for name in TOOL_DESCRIPTIONS
    ]


def get_extra_tools_module():
    """Return the extra_tools_module if configured, else None."""
    path = app_settings.get("mcp", {}).get("extra_tools_module")
    if not path:
        return None
    return __import__(str(path), fromlist=["register_extra_tools"])


def get_all_chat_tools():
    """Return built-in + extra chat tools (same format). Projects can define get_extra_chat_tools() in extra_tools_module."""  # noqa: E501
    result = list(get_chat_tools())
    mod = get_extra_tools_module()
    if mod is not None and hasattr(mod, "get_extra_chat_tools"):
        extra = getattr(mod, "get_extra_chat_tools")()
        if isinstance(extra, list):
            result.extend(extra)
    return result
