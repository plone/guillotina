import json
import pytest

from guillotina.contrib.mcp import tools as mcp_tools


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
