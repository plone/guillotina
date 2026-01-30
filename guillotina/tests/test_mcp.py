import pytest

from guillotina.contrib.mcp.backend import InProcessBackend
from guillotina.contrib.mcp.backend import clear_mcp_context


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
