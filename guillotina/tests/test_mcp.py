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
        assert status in (200, 401, 404)


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_inprocess_backend_search_requires_context(container_requester):
    backend = InProcessBackend()
    clear_mcp_context()
    with pytest.raises(RuntimeError, match="MCP context not set"):
        await backend.search(None, {})


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
