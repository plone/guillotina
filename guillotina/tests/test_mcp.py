from contextlib import asynccontextmanager
from guillotina.contrib.mcp.backend import clear_mcp_context
from guillotina.contrib.mcp.backend import InProcessBackend
from guillotina.contrib.mcp.backend import set_mcp_context
from guillotina.contrib.mcp.chat import _execute_tool
from guillotina.tests import utils
from guillotina.transactions import get_transaction
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import json
import os
import pytest
import sys


NOT_POSTGRES = os.environ.get("DATABASE", "DUMMY") in ("cockroachdb", "DUMMY")
MCP_PG_CATALOG_SETTINGS = {
    "applications": ["guillotina.contrib.mcp", "guillotina.contrib.catalog.pg"],
    "load_utilities": {
        "catalog": {
            "provides": "guillotina.interfaces.ICatalogUtility",
            "factory": "guillotina.contrib.catalog.pg.utility.PGSearchUtility",
        }
    },
}

try:
    import mcp
except ImportError:
    mcp = None

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(mcp is None, reason="mcp package requires Python 3.10+"),
]


@asynccontextmanager
async def _mcp_backend_context(requester):
    request = utils.get_mocked_request(db=requester.db)
    utils.login()
    try:
        async with requester.transaction(request):
            txn = get_transaction()
            root = await txn.manager.get_root()
            container = await root.async_get("guillotina")
            set_mcp_context(container)
            yield InProcessBackend(), container
    finally:
        clear_mcp_context()


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_mcp_service_registered(container_requester):
    async with container_requester as requester:
        resp, status = await requester("GET", "/db/guillotina/@mcp")
        assert status == 200


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
        assert status == 200
        if status == 200 and isinstance(resp, dict):
            assert "result" in resp or "error" in resp


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_inprocess_backend_requires_valid_context(container_requester):
    async with container_requester:
        clear_mcp_context()
        backend = InProcessBackend()
        with pytest.raises(RuntimeError, match="MCP context not set"):
            await backend.search(None, {})
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


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_backend_get_content_by_path_and_uid_returns_serialized(container_requester):
    async with container_requester as requester:
        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "id": "myitem"}),
        )
        assert status == 201
        uid = resp.get("@uid")
        async with _mcp_backend_context(requester) as (backend, container):
            by_path = await backend.get_content(container, "myitem", None)
            by_uid = await backend.get_content(container, None, uid)
        assert by_path.get("@id") and by_path.get("@type") == "Item" and by_path.get("@name") == "myitem"
        assert by_uid.get("@id") == by_path.get("@id") and by_uid.get("@name") == "myitem"


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_backend_get_content_without_view_content_returns_empty(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "id": "secret"}),
        )
        assert status == 201
        _, status = await requester(
            "POST",
            "/db/guillotina/secret/@sharing",
            data=json.dumps(
                {
                    "prinperm": [
                        {
                            "principal": "root",
                            "permission": "guillotina.ViewContent",
                            "setting": "Deny",
                        }
                    ]
                }
            ),
        )
        assert status == 200
        async with _mcp_backend_context(requester) as (backend, container):
            result = await backend.get_content(container, "secret", None)
        assert result == {}


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_backend_list_children_returns_visible_only(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Folder", "id": "folder"}),
        )
        assert status == 201
        _, status = await requester(
            "POST",
            "/db/guillotina/folder/",
            data=json.dumps({"@type": "Item", "id": "visible"}),
        )
        assert status == 201
        _, status = await requester(
            "POST",
            "/db/guillotina/folder/",
            data=json.dumps({"@type": "Item", "id": "hidden"}),
        )
        assert status == 201
        _, status = await requester(
            "POST",
            "/db/guillotina/folder/hidden/@sharing",
            data=json.dumps(
                {
                    "prinperm": [
                        {
                            "principal": "root",
                            "permission": "guillotina.ViewContent",
                            "setting": "Deny",
                        }
                    ]
                }
            ),
        )
        assert status == 200
        async with _mcp_backend_context(requester) as (backend, container):
            result = await backend.list_children(container, "folder", 0, 20)
        assert result["items_total"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0]["@name"] == "visible"


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_backend_list_children_empty_when_no_view_on_container(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Folder", "id": "private"}),
        )
        assert status == 201
        _, status = await requester(
            "POST",
            "/db/guillotina/private/@sharing",
            data=json.dumps(
                {
                    "prinperm": [
                        {
                            "principal": "root",
                            "permission": "guillotina.ViewContent",
                            "setting": "Deny",
                        }
                    ]
                }
            ),
        )
        assert status == 200
        async with _mcp_backend_context(requester) as (backend, container):
            result = await backend.list_children(container, "private", 0, 20)
        assert result["items_total"] == 0
        assert result["items"] == []


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_chat_execute_tool_container_path_scopes(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Folder", "id": "sub"}),
        )
        assert status == 201
        _, status = await requester(
            "POST",
            "/db/guillotina/sub/",
            data=json.dumps({"@type": "Item", "id": "inside"}),
        )
        assert status == 201
        async with _mcp_backend_context(requester) as (backend, _):
            result = await _execute_tool(backend, "list_children", {"container_path": "sub"})
        assert result["items_total"] == 1
        assert result["items"][0]["@name"] == "inside"


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_chat_execute_tool_invalid_container_path_returns_empty(container_requester):
    async with container_requester as requester:
        async with _mcp_backend_context(requester) as (backend, _):
            result = await _execute_tool(backend, "list_children", {"container_path": "missing"})
        assert result["items_total"] == 0
        assert result["items"] == []


@pytest.mark.app_settings({"applications": ["guillotina.contrib.mcp"]})
async def test_backend_search_with_context(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "id": "searchme"}),
        )
        assert status == 201
        async with _mcp_backend_context(requester) as (backend, container):
            result = await backend.search(container, {})
        assert "items" in result
        assert "items_total" in result


@pytest.mark.app_settings(MCP_PG_CATALOG_SETTINGS)
@pytest.mark.skipif(NOT_POSTGRES, reason="Search permission filtering uses PG catalog")
async def test_backend_search_respects_permissions(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "id": "public_item"}),
        )
        assert status == 201
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "id": "private_item"}),
        )
        assert status == 201
        _, status = await requester(
            "POST",
            "/db/guillotina/private_item/@sharing",
            data=json.dumps(
                {
                    "perminhe": [{"permission": "guillotina.AccessContent", "setting": "Deny"}],
                    "roleperm": [],
                }
            ),
        )
        assert status == 200
        async with _mcp_backend_context(requester) as (backend, container):
            result = await backend.search(container, {})
        names = [it.get("@name") for it in result.get("items", []) if it.get("@name")]
        assert "private_item" not in names
        assert "public_item" in names
        assert result["items_total"] >= 1
