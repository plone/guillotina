from guillotina.contrib.mcp import resources as mcp_resources
from guillotina.contrib.mcp import tools as mcp_tools

import json
import pytest


pytestmark = pytest.mark.asyncio

MCP_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.mcp"],
}


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_mcp_tools_list(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp/tools")
        assert status == 200
        names = {tool["name"] for tool in response["tools"]}
        assert "resolve_path" in names
        assert "list_children" in names
        assert "serialize_resource" in names
        assert "notify_modified" in names


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_invoke_resolve_path_tool(container_requester):
    async with container_requester as requester:
        payload = {"tool": "resolve_path", "arguments": {"path": "/"}}
        response, status = await requester(
            "POST", "/db/guillotina/@mcp/tools/invoke", data=json.dumps(payload)
        )
        assert status == 200
        assert response["tool"] == "resolve_path"
        assert response["result"]["resource"]["@type"] == "Container"
        assert response["result"]["path"] == "/"


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_list_children_tool_returns_newly_created_item(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina", data=json.dumps({"@type": "Item", "id": "item-mcp"})
        )
        assert status == 201

        payload = {"tool": "list_children", "arguments": {"path": "/", "limit": 20}}
        response, status = await requester(
            "POST", "/db/guillotina/@mcp/tools/invoke", data=json.dumps(payload)
        )
        assert status == 200
        ids = {item["id"] for item in response["result"]["items"]}
        assert "item-mcp" in ids


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_cache_revision_is_bumped_by_subscriber(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp")
        assert status == 200
        before = response["mcp"]["cache_revision"]

        _, status = await requester(
            "POST", "/db/guillotina", data=json.dumps({"@type": "Item", "id": "item-cache"})
        )
        assert status == 201

        response, status = await requester("GET", "/db/guillotina/@mcp")
        assert status == 200
        assert response["mcp"]["cache_revision"] > before


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_invoke_unknown_tool_returns_400(container_requester):
    async with container_requester as requester:
        payload = {"tool": "does-not-exist", "arguments": {}}
        response, status = await requester(
            "POST", "/db/guillotina/@mcp/tools/invoke", data=json.dumps(payload)
        )
        assert status == 400
        assert "Unknown MCP tool" in response["reason"]


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_list_children_tool_pagination(container_requester):
    async with container_requester as requester:
        for i in range(1, 106):
            await requester("POST", "/db/guillotina", data=json.dumps({"@type": "Item", "id": f"item-{i}"}))
        payload = {"tool": "list_children", "arguments": {"path": "/", "limit": 50, "page": 1}}
        response, status = await requester(
            "POST", "/db/guillotina/@mcp/tools/invoke", data=json.dumps(payload)
        )
        assert status == 200
        assert response["result"]["limit"] == 50
        assert response["result"]["page"] == 1
        assert response["result"]["truncated"] is True
        assert len(response["result"]["items"]) == 50

        payload["arguments"]["page"] = 3
        response, status = await requester(
            "POST", "/db/guillotina/@mcp/tools/invoke", data=json.dumps(payload)
        )
        assert status == 200
        assert response["result"]["page"] == 3
        assert response["result"]["truncated"] is False
        assert len(response["result"]["items"]) == 5


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_list_children_uses_catalog_when_available(container_requester, monkeypatch):
    class FakeCatalog:
        async def search(self, context, query):
            assert query["path__starts"] == "/"
            return {
                "items": [
                    {
                        "id": "catalog-child",
                        "type_name": "Item",
                        "title": "From catalog",
                        "path": "/catalog-child",
                    }
                ],
                "items_total": 1,
            }

    async def fail_async_items(**kwargs):
        raise AssertionError("async_items fallback should not be used when catalog utility is available")

    monkeypatch.setattr(mcp_tools, "query_utility", lambda iface: FakeCatalog())
    monkeypatch.setattr(mcp_tools, "_list_children_from_async_items", fail_async_items)

    async with container_requester as requester:
        payload = {"tool": "list_children", "arguments": {"path": "/", "limit": 20}}
        response, status = await requester(
            "POST", "/db/guillotina/@mcp/tools/invoke", data=json.dumps(payload)
        )
        assert status == 200
        assert response["result"]["items_total"] == 1
        assert response["result"]["items"][0]["id"] == "catalog-child"


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_mcp_root_lists_tools_and_resources(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp")
        assert status == 200
        assert "mcp" in response
        assert "tools" in response
        assert "resources" in response
        assert isinstance(response["resources"], list)
        assert len(response["resources"]) > 0
        # Every resource must expose discovery fields
        for res in response["resources"]:
            assert "uri" in res
            assert "name" in res
            assert "endpoint" in res


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_mcp_resources_listing(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp/resources")
        assert status == 200
        names = {r["name"] for r in response["resources"]}
        # All default resources must be registered
        for expected in ("info", "health", "config", "users", "catalog", "summary"):
            assert expected in names, f"Missing resource: {expected}"


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_mcp_metadata_includes_resource_count(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp")
        assert status == 200
        assert response["mcp"]["resource_count"] == len(response["resources"])


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_resource_info(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp/resources/info")
        assert status == 200
        assert "version" in response
        assert "container_id" in response


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_resource_health(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp/resources/health")
        assert status == 200
        assert response["status"] in ("ok", "degraded")
        assert "db" in response


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_resource_config(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp/resources/config")
        assert status == 200
        assert "mcp" in response
        assert response["mcp"]["enabled"] is True
        assert "applications" in response


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_resource_catalog(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp/resources/catalog")
        assert status == 200
        assert "available" in response


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_resource_summary(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp/resources/summary?path=/")
        assert status == 200
        assert response["@type"] == "Container"
        assert "path" in response


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_unknown_resource_returns_404(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp/resources/nonexistent")
        assert status == 404


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_server_status(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp/server/status")
        assert status == 200
        assert "ready" in response
        assert "mcp" in response


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_resource_registry_matches_default_resources(container_requester):
    """The registry must contain exactly the resources declared in default_resources()."""
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@mcp/resources")
        assert status == 200
        registered_names = {r["name"] for r in response["resources"]}
        default_names = {name for name, *_ in mcp_resources.default_resources()}
        assert registered_names == default_names
