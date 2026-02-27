from guillotina import configure
from guillotina._settings import app_settings
from guillotina.component import query_utility
from guillotina.contrib.mcp.backend import get_mcp_context
from guillotina.contrib.mcp.backend import InProcessBackend
from guillotina.contrib.mcp.interfaces import IMCPDescriptionExtras
from guillotina.contrib.mcp.interfaces import IMCPToolProvider
from zope.interface import implementer

import json
import typing


TOOL_DESCRIPTIONS = {
    "search": (
        "Search the catalog. container_path is optional (default: current context). "
        "query must be an object (dict) with keys: type_name, term, _size, _from, _sort_asc, _sort_des; "
        "date filters: fieldname__gte, fieldname__lte (ISO 8601, e.g. 2026-02-09T00:00:00Z)."
    ),
    "count": (
        "Count catalog results. container_path is optional. query must be an object (dict), same keys as search "
        "(no _size/_from/_sort_asc/_sort_des). Date filters: fieldname__gte, fieldname__lte (ISO 8601)."
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
                "description": "Search query object. Keys: type_name, _size, fieldname__gte, fieldname__lte (dates ISO 8601).",  # noqa: E501
            },
        },
    },
    "count": {
        "properties": {
            "container_path": {"type": "string", "description": "Optional path relative to container."},
            "query": {
                "type": "object",
                "description": "Count query object. Keys: type_name, fieldname__gte, fieldname__lte (dates ISO 8601).",
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


def _normalize_query(
    query: typing.Optional[typing.Union[typing.Dict[str, typing.Any], str]],
) -> typing.Dict[str, typing.Any]:
    if query is None:
        return {}
    if isinstance(query, dict):
        return query
    if isinstance(query, str):
        try:
            parsed = json.loads(query)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _get_description_extras():
    extras = dict(app_settings.get("mcp", {}).get("description_extras") or {})
    util = query_utility(IMCPDescriptionExtras)
    if util is not None:
        for k, v in (util() or {}).items():
            extras[k] = (extras.get(k) or "") + (" " + v if v else "")
    return extras


def _tool_description(name: str) -> str:
    extras = _get_description_extras()
    return (TOOL_DESCRIPTIONS[name] + " " + (extras.get(name) or "")).strip()


def _tool_input_schema(name: str) -> typing.Dict[str, typing.Any]:
    return {"type": "object", **CHAT_PARAM_SCHEMAS[name]}


def _tool_definition(name: str) -> typing.Dict[str, typing.Any]:
    return {
        "name": name,
        "description": _tool_description(name),
        "input_schema": _tool_input_schema(name),
    }


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


@implementer(IMCPToolProvider)
@configure.utility(provides=IMCPToolProvider, name="search")
class SearchToolProvider:
    def __init__(self):
        self.backend = InProcessBackend()

    def get_tool_definition(self) -> typing.Dict[str, typing.Any]:
        return _tool_definition("search")

    async def execute(self, arguments: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        args = arguments if isinstance(arguments, dict) else {}
        context = await _context_for_path(args.get("container_path"))
        if context is None:
            return {"items": [], "items_total": 0}
        query = _normalize_query(args.get("query"))
        return await self.backend.search(context, query)


@implementer(IMCPToolProvider)
@configure.utility(provides=IMCPToolProvider, name="count")
class CountToolProvider:
    def __init__(self):
        self.backend = InProcessBackend()

    def get_tool_definition(self) -> typing.Dict[str, typing.Any]:
        return _tool_definition("count")

    async def execute(self, arguments: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        args = arguments if isinstance(arguments, dict) else {}
        context = await _context_for_path(args.get("container_path"))
        if context is None:
            return {"count": 0}
        query = _normalize_query(args.get("query"))
        value = await self.backend.count(context, query)
        return {"count": value}


@implementer(IMCPToolProvider)
@configure.utility(provides=IMCPToolProvider, name="get_content")
class GetContentToolProvider:
    def __init__(self):
        self.backend = InProcessBackend()

    def get_tool_definition(self) -> typing.Dict[str, typing.Any]:
        return _tool_definition("get_content")

    async def execute(self, arguments: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        args = arguments if isinstance(arguments, dict) else {}
        context = await _context_for_path(args.get("container_path"))
        if context is None:
            return {}
        return await self.backend.get_content(context, args.get("path"), args.get("uid"))


@implementer(IMCPToolProvider)
@configure.utility(provides=IMCPToolProvider, name="list_children")
class ListChildrenToolProvider:
    def __init__(self):
        self.backend = InProcessBackend()

    def get_tool_definition(self) -> typing.Dict[str, typing.Any]:
        return _tool_definition("list_children")

    async def execute(self, arguments: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        args = arguments if isinstance(arguments, dict) else {}
        context = await _context_for_path(args.get("container_path"))
        if context is None:
            return {"items": [], "items_total": 0}
        try:
            from_index = int(args.get("from_index", 0))
        except (TypeError, ValueError):
            from_index = 0
        try:
            page_size = int(args.get("page_size", 20))
        except (TypeError, ValueError):
            page_size = 20
        return await self.backend.list_children(context, args.get("path") or "", from_index, page_size)


def get_chat_tools():
    """Return built-in tool definitions in the format expected by LiteLLM for @chat (all providers)."""
    descriptions = {name: _tool_description(name) for name in TOOL_DESCRIPTIONS}
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": descriptions[name],
                "parameters": _tool_input_schema(name),
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
