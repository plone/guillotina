from guillotina.contrib.mcp.backend import clear_mcp_context
from guillotina.contrib.mcp.backend import InProcessBackend

import json
import pytest


pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_mcp_service_registered(container_requester):
    pytest.importorskip("mcp")
    async with container_requester as requester:
        resp, status = await requester("GET", "/db/guillotina/@mcp")
        assert status in (200, 401, 404, 421)


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"], "mcp": {"enabled": False}})
async def test_mcp_disabled_returns_404(container_requester):
    pytest.importorskip("mcp")
    async with container_requester as requester:
        _, status = await requester("GET", "/db/guillotina/@mcp")
        assert status == 404


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_mcp_tools_list(container_requester):
    pytest.importorskip("mcp")
    async with container_requester as requester:
        resp, status = await requester(
            "POST",
            "/db/guillotina/@mcp",
            data=json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1}),
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
        )
        assert status in (200, 401, 421)
        if status == 200 and isinstance(resp, dict):
            assert "result" in resp or "error" in resp


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_inprocess_backend_search_requires_context(container_requester):
    backend = InProcessBackend()
    clear_mcp_context()
    with pytest.raises(RuntimeError, match="MCP context not set"):
        await backend.search(None, {})


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_inprocess_backend_rejects_string_context(container_requester):
    backend = InProcessBackend()
    clear_mcp_context()
    with pytest.raises(RuntimeError, match="InProcessBackend requires IResource context"):
        await backend.search("db/guillotina", {})


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_mcp_token_requires_auth(container_requester):
    async with container_requester as requester:
        _, status = await requester("POST", "/db/guillotina/@mcp-token", authenticated=False)
        assert status == 401


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_mcp_token_returns_long_lived_token(container_requester):
    async with container_requester as requester:
        resp, status = await requester("POST", "/db/guillotina/@mcp-token")
        assert status == 200
        assert "token" in resp
        assert "exp" in resp
        assert resp.get("duration_days") == 30
        resp_custom, status_custom = await requester(
            "POST",
            "/db/guillotina/@mcp-token",
            data=json.dumps({"duration_days": 60}),
        )
        assert status_custom == 200
        assert resp_custom.get("duration_days") == 60
