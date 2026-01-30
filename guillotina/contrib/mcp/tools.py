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


def _get_description_extras():
    from guillotina.component import query_utility

    extras = dict(app_settings.get("mcp", {}).get("description_extras") or {})
    util = query_utility(IMCPDescriptionExtras)
    if util is not None:
        for k, v in (util() or {}).items():
            extras[k] = (extras.get(k) or "") + (" " + v if v else "")
    return extras


def register_tools(mcp_server, backend):
    def _context_for_path(container_path: typing.Optional[str]):
        ctx = get_mcp_context()
        if ctx is None:
            return None
        if container_path:
            from guillotina.utils import navigate_to

            try:
                return navigate_to(ctx, "/" + container_path.strip("/"))
            except KeyError:
                return None
        return ctx

    extras = _get_description_extras()

    @mcp_server.tool(description=(TOOL_DESCRIPTIONS["search"] + " " + (extras.get("search") or "")).strip())
    async def search(
        container_path: typing.Optional[str] = None,
        query: typing.Optional[typing.Dict[str, str]] = None,
    ) -> dict:
        context = _context_for_path(container_path)
        if context is None and container_path is None:
            return {"items": [], "items_total": 0}
        q = query or {}
        return await backend.search(context, q)

    @mcp_server.tool(description=(TOOL_DESCRIPTIONS["count"] + " " + (extras.get("count") or "")).strip())
    async def count(
        container_path: typing.Optional[str] = None,
        query: typing.Optional[typing.Dict[str, str]] = None,
    ):
        context = _context_for_path(container_path)
        if context is None and container_path is None:
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
        context = _context_for_path(container_path)
        if context is None and container_path is None:
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
        context = _context_for_path(container_path)
        if context is None and container_path is None:
            return {"items": [], "items_total": 0}
        return await backend.list_children(context, path or "", from_index, page_size)
