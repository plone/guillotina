import json

import pytest

from guillotina.tests.mcp.test_mcp import PROTOCOL_HEADERS, _skip_if_protocol_unavailable
from guillotina.tests.oauth.conftest import OAUTH_MCP_SETTINGS, authorize_code, register_client, token_from_code

pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_mcp_protected_resource_metadata(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester("GET", "/db/guillotina/.well-known/oauth-protected-resource")
        assert status == 200
        assert response["resource"].endswith("/db/guillotina/@mcp/protocol")
        assert response["authorization_servers"][0].endswith("/db/guillotina")


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_mcp_without_token_challenges(container_install_requester):
    async with container_install_requester as requester:
        _value, status, headers = await requester.make_request("POST", "/db/guillotina/@mcp/protocol", data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}), headers=PROTOCOL_HEADERS, authenticated=False)
        assert status == 401
        assert "resource_metadata" in headers["WWW-Authenticate"]


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_mcp_with_oauth_token(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client, resource="http://localhost/db/guillotina/@mcp/protocol")
        token = await token_from_code(requester, client, code, verifier)
        response, status = await requester("POST", "/db/guillotina/@mcp/protocol", data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}), headers=PROTOCOL_HEADERS, auth_type="Bearer", token=token["access_token"])
        _skip_if_protocol_unavailable(response, status)
        assert status == 200


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_mcp_rejects_missing_mcp_audience(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client, resource="http://localhost/db/guillotina")
        token = await token_from_code(requester, client, code, verifier)
        _response, status = await requester("POST", "/db/guillotina/@mcp/protocol", data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}), headers=PROTOCOL_HEADERS, auth_type="Bearer", token=token["access_token"])
        assert status == 401
