from guillotina.contrib.mcp import resources as mcp_resources

import json
import pytest


pytestmark = pytest.mark.asyncio

MCP_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.mcp"],
}

PROTOCOL_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def _skip_if_protocol_unavailable(response, status):
    if status != 503:
        return
    reason = ""
    if isinstance(response, dict):
        reason = str(response.get("reason") or response.get("message") or "")
    known_causes = (
        "MCP SDK missing",
        "Install \"guillotina[mcp]\"",
        "MCP registry utility is not available",
    )
    if any(cause in reason for cause in known_causes):
        detail = f": {reason}" if reason else ""
        pytest.skip(f"MCP protocol unavailable in this environment{detail}")


async def _protocol(requester, method, params=None, id=1):
    payload = {"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}}
    response, status = await requester(
        "POST",
        "/db/guillotina/@mcp/protocol",
        data=json.dumps(payload),
        headers=PROTOCOL_HEADERS,
    )
    _skip_if_protocol_unavailable(response, status)
    return response, status


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_initialize(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(
            requester,
            "initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        )
        assert status == 200
        assert response["jsonrpc"] == "2.0"
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert "tools" in response["result"]["capabilities"]
        assert "resources" in response["result"]["capabilities"]
        assert response["result"]["serverInfo"]["name"] == "guillotina-mcp"


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_tools_list(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(requester, "tools/list")
        assert status == 200
        names = {t["name"] for t in response["result"]["tools"]}
        assert "search" in names
        assert "list_children" in names
        assert "resolve_path" in names
        assert "serialize_resource" in names
        assert "notify_modified" in names


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_tools_call_resolve_path(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(
            requester,
            "tools/call",
            params={"name": "resolve_path", "arguments": {"path": "/"}},
        )
        assert status == 200
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["path"] == "/"
        assert content["resource"]["@type"] == "Container"


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_tools_call_list_children(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST", "/db/guillotina", data=json.dumps({"@type": "Item", "id": "item-proto"})
        )
        assert status == 201

        response, status = await _protocol(
            requester,
            "tools/call",
            params={"name": "list_children", "arguments": {"path": "/", "limit": 20}},
        )
        assert status == 200
        content = json.loads(response["result"]["content"][0]["text"])
        ids = {item["id"] for item in content["items"]}
        assert "item-proto" in ids


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_tools_call_unknown_tool_returns_error(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(
            requester,
            "tools/call",
            params={"name": "does-not-exist", "arguments": {}},
        )
        assert status == 200
        # Unknown tool: SDK returns a tool result with isError=True (not a JSON-RPC error)
        assert response["result"]["isError"] is True


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_resources_list(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(requester, "resources/list")
        assert status == 200
        names = {r["name"] for r in response["result"]["resources"]}
        for expected in ("info", "health", "config", "users", "catalog", "summary"):
            assert expected in names, f"Missing resource: {expected}"


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_resources_read_info(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(
            requester,
            "resources/read",
            params={"uri": "guillotina://resources/info"},
        )
        assert status == 200
        content = json.loads(response["result"]["contents"][0]["text"])
        assert "version" in content
        assert "container_id" in content


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_resources_read_summary_with_path(container_requester):
    """resources/read for summary accepts ?path= URI query params (server.py uri matching fix)."""
    async with container_requester as requester:
        # Without path — should return container summary
        response, status = await _protocol(
            requester,
            "resources/read",
            params={"uri": "guillotina://resources/summary"},
        )
        assert status == 200
        content = json.loads(response["result"]["contents"][0]["text"])
        assert content["path"] == "/"
        assert content["@type"] == "Container"

        # With ?path=/ — same result, proves URI query params are forwarded
        response, status = await _protocol(
            requester,
            "resources/read",
            params={"uri": "guillotina://resources/summary?path=/"},
        )
        assert status == 200
        content = json.loads(response["result"]["contents"][0]["text"])
        assert content["path"] == "/"
        assert content["@type"] == "Container"


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_requires_accept_header(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/@mcp/protocol",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}),
            headers={"Content-Type": "application/json"},
        )
        _skip_if_protocol_unavailable(response, status)
        assert status == 406


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_invalid_json_rpc_returns_400(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/@mcp/protocol",
            data=json.dumps({"not": "jsonrpc"}),
            headers=PROTOCOL_HEADERS,
        )
        _skip_if_protocol_unavailable(response, status)
        assert status == 400


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_unknown_action_returns_404(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/@mcp/not-a-real-action",
            data=json.dumps({}),
            headers=PROTOCOL_HEADERS,
        )
        assert status == 404


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_resource_registry_matches_defaults(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(requester, "resources/list")
        assert status == 200
        registered_names = {r["name"] for r in response["result"]["resources"]}
        default_names = {res[0] for res in mcp_resources.default_resources()}
        assert registered_names == default_names


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_invoke_resolve_path_tool(container_requester):
    """Kept as an alias — now uses the JSON-RPC protocol path."""
    async with container_requester as requester:
        response, status = await _protocol(
            requester,
            "tools/call",
            params={"name": "resolve_path", "arguments": {"path": "/"}},
        )
        assert status == 200
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["resource"]["@type"] == "Container"
        assert content["path"] == "/"
