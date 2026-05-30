import functools
from typing import Any, Awaitable, Callable, Dict, List, Tuple

from guillotina.catalog.catalog import DefaultSearchUtility
from guillotina.component import query_multi_adapter, query_utility
from guillotina.contrib.mcp.security import (
    has_permission,
    require_access_content,
    require_permission,
    require_view_content,
)
from guillotina.interfaces import IResourceSerializeToJson, IResourceSerializeToJsonSummary
from guillotina.interfaces.catalog import ICatalogUtility
from guillotina.utils import get_content_path, get_current_container, navigate_to


ToolHandler = Callable[[Any, Any, Dict[str, Any]], Awaitable[Dict[str, Any]]]

RESOLVE_PATH_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Absolute or relative Guillotina path", "default": "/"},
        "include_serialized": {
            "type": "boolean",
            "default": False,
            "description": (
                "When true, include full JSON from Guillotina serializers "
                "(same as GET on the resource). Default response is minimal: id, @type, title, path."
            ),
        },
    },
}

LIST_CHILDREN_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Absolute or relative Guillotina path", "default": "/"},
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 200,
            "default": 50,
            "description": "Number of children to return per page. Hard cap is 200.",
        },
        "page": {
            "type": "integer",
            "minimum": 1,
            "default": 1,
            "description": "Page number (1-based). Use with limit to paginate.",
        },
        "include_serialized": {
            "type": "boolean",
            "default": False,
            "description": "When true, include full serialized JSON per child (heavier response).",
        },
    },
}

SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "object",
            "description": (
                "Guillotina catalog query object. "
                "Supports: type_name, creators, tags, path__startswith, creation_date__gte, etc. "
                "Use 'b_size' (max 1000) to set page size and 'b_start' to offset for pagination. "
                "Use '_metadata' as a comma-separated list of field names to limit returned fields "
                "and reduce response size, e.g. '_metadata': 'id,type_name,title,path'."
            ),
        },
    },
    "required": ["query"],
}


def _normalize_path(raw_path: Any) -> str:
    clean = str(raw_path or "/").strip() or "/"
    if clean.startswith("/"):
        return clean
    return clean


def _coerce_limit(value: Any, default: int) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(limit, 200))


def _resource_summary(resource: Any, path_hint: str = "") -> Dict[str, Any]:
    path = path_hint or get_content_path(resource)
    return {
        "id": getattr(resource, "id", getattr(resource, "__name__", None)),
        "@type": getattr(resource, "type_name", resource.__class__.__name__),
        "title": getattr(resource, "title", None),
        "path": path or "/",
    }


async def _serialize_resource(resource: Any, request: Any) -> Dict[str, Any]:
    require_access_content(resource)
    require_view_content(resource)
    serializer = query_multi_adapter((resource, request), IResourceSerializeToJson)
    if serializer is None:
        serializer = query_multi_adapter((resource, request), IResourceSerializeToJsonSummary)
    if serializer is None:
        return _resource_summary(resource)
    return await serializer()


async def _resolve_target(context: Any, raw_path: Any) -> Tuple[Any, str]:
    clean = _normalize_path(raw_path)
    if clean in ("", "/"):
        container = get_current_container()
        if container is None:
            raise ValueError("Container is not available in current task vars")
        return container, "/"

    if clean.startswith("/"):
        container = get_current_container()
        if container is None:
            raise ValueError("Container is not available in current task vars")
        return await navigate_to(container, clean), clean

    return await navigate_to(context, clean), clean


async def resolve_path_tool(context: Any, request: Any, arguments: Dict[str, Any]) -> Dict[str, Any]:
    target, resolved_path = await _resolve_target(context, arguments.get("path", "/"))
    require_access_content(target)
    result = {
        "path": resolved_path,
        "resource": _resource_summary(target, get_content_path(target)),
    }
    if bool(arguments.get("include_serialized", False)):
        result["serialized"] = await _serialize_resource(target, request)
    return result


async def list_children_tool(
    context: Any, request: Any, arguments: Dict[str, Any], default_limit: int = 50
) -> Dict[str, Any]:
    target, resolved_path = await _resolve_target(context, arguments.get("path", "/"))
    require_access_content(target)
    if not hasattr(target, "async_items"):
        raise ValueError("Target path does not point to a folder-like resource")

    limit = _coerce_limit(arguments.get("limit", default_limit), default_limit)
    page = max(1, int(arguments.get("page", 1)))
    include_serialized = bool(arguments.get("include_serialized", False))

    catalog_result = await _list_children_from_catalog(
        target=target,
        request=request,
        resolved_path=resolved_path,
        limit=limit,
        include_serialized=include_serialized,
    )
    if catalog_result is not None:
        return catalog_result

    return await _list_children_from_async_items(
        target=target,
        request=request,
        resolved_path=resolved_path,
        limit=limit,
        page=page,
        include_serialized=include_serialized,
    )


def _get_catalog_utility():
    catalog = query_utility(ICatalogUtility)
    if catalog is None or catalog.__class__ == DefaultSearchUtility:
        return None
    return catalog


def _child_prefix(path: str) -> str:
    if path in ("", "/"):
        return "/"
    return path.rstrip("/") + "/"


async def _serialize_from_catalog_path(path: str, request: Any) -> Dict[str, Any]:
    container = get_current_container()
    if container is None:
        raise ValueError("Container is not available in current task vars")
    resource = await navigate_to(container, path)
    return await _serialize_resource(resource, request)


def _summary_from_catalog_hit(hit: Dict[str, Any], fallback_path: str = "") -> Dict[str, Any]:
    return {
        "id": hit.get("id", hit.get("@name")),
        "@type": hit.get("type_name", hit.get("@type", "Resource")),
        "title": hit.get("title"),
        "path": hit.get("path", fallback_path or ""),
    }


async def _list_children_from_catalog(
    *, target: Any, request: Any, resolved_path: str, limit: int, include_serialized: bool
) -> Any:
    catalog = _get_catalog_utility()
    if catalog is None:
        return None

    query = {
        "path__starts": _child_prefix(resolved_path),
        "depth": "1",
        "_size": str(limit + 1),
        "_sort_asc": "id",
        "_metadata": "id,type_name,title,path",
    }
    result = await catalog.search(target, query)
    hits = list(result.get("items", []))
    truncated = bool(result.get("items_total", len(hits)) > limit or len(hits) > limit)
    hits = hits[:limit]

    items: List[Dict[str, Any]] = []
    for hit in hits:
        item_summary = _summary_from_catalog_hit(hit)
        if include_serialized:
            path = item_summary.get("path", "")
            if isinstance(path, str) and path:
                item_summary["serialized"] = await _serialize_from_catalog_path(path, request)
        items.append(item_summary)

    return {
        "path": resolved_path,
        "limit": limit,
        "items_total": len(items),
        "truncated": truncated,
        "items": items,
    }


async def _list_children_from_async_items(
    *, target: Any, request: Any, resolved_path: str, limit: int, page: int, include_serialized: bool
) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    truncated = False
    count = 0
    start_index = (page - 1) * limit
    end_index = page * limit

    async for _, child in target.async_items():
        if not has_permission("guillotina.AccessContent", child):
            continue
        if count >= start_index and count < end_index:
            item_summary = _resource_summary(child, get_content_path(child))
            if include_serialized:
                item_summary["serialized"] = await _serialize_resource(child, request)
            items.append(item_summary)
        elif count >= end_index:
            truncated = True
            break
        count += 1

    return {
        "path": resolved_path,
        "limit": limit,
        "page": page,
        "items_total": len(items),
        "truncated": truncated,
        "items": items,
    }


async def search_tool(context: Any, request: Any, arguments: Dict[str, Any]) -> Dict[str, Any]:
    require_permission("guillotina.SearchContent", context)
    catalog = _get_catalog_utility()
    if catalog is None:
        raise ValueError("Catalog utility is not available")
    query = arguments.get("query", {})
    result = await catalog.search(context, query)
    return {"query": query, "result": result}


def default_tools(default_child_limit: int = 50) -> List[Tuple[str, str, Dict[str, Any], ToolHandler, bool]]:
    return [
        (
            "resolve_path",
            (
                "Resolve a Guillotina path. By default returns minimal metadata "
                "(id, @type, title, path). Set include_serialized=true for full JSON (like GET)."
            ),
            RESOLVE_PATH_SCHEMA,
            resolve_path_tool,
            True,
        ),
        (
            "list_children",
            (
                "List child resources from a folder-like Guillotina resource. "
                "Max 200 per page; use 'page' to paginate. "
                "Set include_serialized=true for full JSON per child."
            ),
            LIST_CHILDREN_SCHEMA,
            functools.partial(list_children_tool, default_limit=default_child_limit),
            True,
        ),
        (
            "search",
            (
                "Search for resources using the Guillotina catalog. "
                "Supports filtering by type_name, creators, path, dates, and more. "
                "Paginate with 'b_start' (offset) and 'b_size' (page size, max 1000). "
                "Limit returned fields with '_metadata' (e.g. 'id,type_name,title,path,creators')."
            ),
            SEARCH_SCHEMA,
            search_tool,
            True,
        ),
    ]
