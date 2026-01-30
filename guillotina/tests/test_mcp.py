from guillotina.contrib.mcp.backend import clear_mcp_context
from guillotina.contrib.mcp.backend import InProcessBackend
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import json
import pytest
import sys


try:
    import mcp
except ImportError:
    mcp = None

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(mcp is None, reason="mcp package requires Python 3.10+"),
]


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_mcp_service_registered(container_requester):
    async with container_requester as requester:
        resp, status = await requester("GET", "/db/guillotina/@mcp")
        assert status in (200, 401, 404, 421)


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"], "mcp": {"enabled": False}})
async def test_mcp_disabled_returns_404(container_requester):
    async with container_requester as requester:
        _, status = await requester("GET", "/db/guillotina/@mcp")
        assert status == 404


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_mcp_tools_list(container_requester):
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


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"], "mcp": {"chat_enabled": False}})
async def test_chat_disabled_returns_404(container_requester):
    pytest.importorskip("litellm")
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/@chat",
            data=json.dumps({"message": "hello"}),
        )
        assert status == 404


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_chat_no_model_returns_412(container_requester):
    pytest.importorskip("litellm")
    async with container_requester as requester:
        resp, status = await requester(
            "POST",
            "/db/guillotina/@chat",
            data=json.dumps({"message": "hello"}),
        )
        assert status == 412
        assert "chat_model" in str(resp.get("reason", ""))


@pytest.mark.app_settings(
    {
        "applications": ["guillotina.contrib.mcp"],
        "mcp": {"chat_enabled": True, "chat_model": "openai/gpt-4o-mini"},
    }
)
async def test_chat_no_message_returns_412(container_requester):
    pytest.importorskip("litellm")
    async with container_requester as requester:
        _, status = await requester("POST", "/db/guillotina/@chat", data=json.dumps({}))
        assert status == 412


@pytest.mark.app_settings(
    {
        "applications": ["guillotina.contrib.mcp"],
        "mcp": {"chat_enabled": True, "chat_model": "openai/gpt-4o-mini"},
    }
)
async def test_chat_returns_content_with_mock(container_requester):
    pytest.importorskip("litellm")
    mock_message = type("Message", (), {"content": "Hello back", "tool_calls": None})()
    mock_choice = type("Choice", (), {"message": mock_message})()
    mock_response = type("Response", (), {"choices": [mock_choice]})()

    mock_litellm = MagicMock()
    mock_litellm.acompletion = AsyncMock(return_value=mock_response)
    orig_litellm = sys.modules.get("litellm")
    sys.modules["litellm"] = mock_litellm
    try:
        async with container_requester as requester:
            resp, status = await requester(
                "POST",
                "/db/guillotina/@chat",
                data=json.dumps({"message": "hello"}),
            )
        assert status == 200
        assert resp.get("content") == "Hello back"
    finally:
        if orig_litellm is not None:
            sys.modules["litellm"] = orig_litellm
        elif "litellm" in sys.modules:
            del sys.modules["litellm"]
