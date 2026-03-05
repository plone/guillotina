from guillotina import __version__
from guillotina import app_settings
from guillotina.component import query_utility
from guillotina.interfaces.catalog import ICatalogUtility
from guillotina.transactions import get_transaction
from guillotina.utils import get_content_path
from guillotina.utils import get_current_container
from guillotina.utils import navigate_to
from typing import Any
from typing import Dict


async def mcp_info_resource(request) -> Dict[str, Any]:
    container = get_current_container()
    return {
        "version": __version__,
        "container_id": getattr(container, "id", None) if container else None,
        "container_path": get_content_path(container) if container else None,
        "enabled_addons": getattr(container, "addons", []),
    }


async def mcp_health_resource(request) -> Dict[str, Any]:
    db_status = "unknown"
    try:
        txn = get_transaction()
        if txn and txn.storage:
            conn = await txn.get_connection()
            if conn:
                db_status = "ok"
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "cache": "ok",  # stub - extend if cache utility is available
    }


async def mcp_config_resource(request) -> Dict[str, Any]:
    mcp_settings = app_settings.get("mcp", {})
    return {
        "mcp": {
            "enabled": mcp_settings.get("enabled", False),
            "server_name": mcp_settings.get("server_name", "guillotina-mcp"),
            "default_child_limit": mcp_settings.get("default_child_limit", 50),
        },
        "applications": app_settings.get("applications", []),
    }


async def mcp_users_resource(request) -> Dict[str, Any]:
    """
    Returns a list of users if dbusers contrib is enabled.
    """
    container = get_current_container()
    if not container:
        return {"error": "No container available"}

    try:
        users_folder = await navigate_to(container, "users")
    except (KeyError, AttributeError):
        return {
            "error": "Users folder not found. Ensure guillotina.contrib.dbusers is enabled.",
            "users": [],
        }

    catalog = query_utility(ICatalogUtility)
    if catalog:
        try:
            query = {
                "type_name": "User",
                "_metadata": "id,user_name,user_email,user_roles,user_groups",
            }
            result = await catalog.search(container, query)
            users = []
            for hit in result.get("items", []):
                users.append(
                    {
                        "id": hit.get("id"),
                        "name": hit.get("user_name"),
                        "email": hit.get("user_email"),
                        "roles": hit.get("user_roles", []),
                        "groups": hit.get("user_groups", []),
                    }
                )
            return {"users": users}
        except Exception:
            # Catalog search failed, fall back to async_items
            pass

    users = []
    try:
        async for user_id, user in users_folder.async_items():
            users.append(
                {
                    "id": user_id,
                    "name": getattr(user, "name", None),
                    "email": getattr(user, "email", None),
                    "roles": list(getattr(user, "user_roles", [])),
                    "groups": list(getattr(user, "user_groups", [])),
                }
            )
    except Exception as e:
        return {"error": f"Failed to list users: {str(e)}", "users": []}

    return {"users": users}


async def mcp_catalog_resource(request) -> Dict[str, Any]:
    catalog = query_utility(ICatalogUtility)
    if catalog is None:
        return {
            "available": False,
            "note": "No catalog utility configured.",
        }

    container = get_current_container()
    return {
        "available": True,
        "catalog_type": catalog.__class__.__name__,
        "container": getattr(container, "id", None) if container else None,
    }


async def mcp_summary_resource(request) -> Dict[str, Any]:
    path = request.query.get("path", "/") if hasattr(request, "query") else "/"
    container = get_current_container()
    if not container:
        return {"error": "No container available"}

    try:
        if path == "/":
            resource = container
        else:
            resource = await navigate_to(container, path)

        summary = {
            "path": get_content_path(resource),
            "id": getattr(resource, "id", getattr(resource, "__name__", None)),
            "@type": getattr(resource, "type_name", resource.__class__.__name__),
            "title": getattr(resource, "title", None),
        }

        # Add child count if it's a folder-like resource
        if hasattr(resource, "async_len"):
            try:
                summary["children_count"] = await resource.async_len()
            except Exception:
                pass

        return summary
    except (KeyError, AttributeError) as e:
        return {"error": f"Resource not found at path: {path}", "details": str(e)}


def default_resources():
    return [
        (
            "info",
            "guillotina://resources/info",
            "Guillotina version, container id and enabled add-ons.",
            "@mcp/resources/info",
            mcp_info_resource,
        ),
        (
            "health",
            "guillotina://resources/health",
            "Database and cache health status.",
            "@mcp/resources/health",
            mcp_health_resource,
        ),
        (
            "config",
            "guillotina://resources/config",
            "MCP settings and loaded applications.",
            "@mcp/resources/config",
            mcp_config_resource,
        ),
        (
            "users",
            "guillotina://resources/users",
            "List users registered in the container (dbusers).",
            "@mcp/resources/users",
            mcp_users_resource,
        ),
        (
            "catalog",
            "guillotina://resources/catalog",
            "Catalog availability and type info.",
            "@mcp/resources/catalog",
            mcp_catalog_resource,
        ),
        (
            "summary",
            "guillotina://resources/summary",
            "Summary of a resource at a given path (accepts ?path=/).",
            "@mcp/resources/summary",
            mcp_summary_resource,
        ),
    ]
