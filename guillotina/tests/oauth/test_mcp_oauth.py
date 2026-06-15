import json
from urllib.parse import parse_qs, urlencode, urlparse

import jwt
import pytest

from guillotina import app_settings
from guillotina.contrib.oauth.utils.crypto import access_token_signing_key
from guillotina.tests.mcp.test_mcp import PROTOCOL_HEADERS, _skip_if_protocol_unavailable
from guillotina.tests.oauth.conftest import (
    OAUTH_MCP_SETTINGS,
    authorize_code,
    oauth_csrf_from_body,
    register_client,
    requires_pg,
    token_from_code,
    verifier_pair,
)


pytestmark = [pytest.mark.asyncio, requires_pg]


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_mcp_protected_resource_metadata(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester("GET", "/db/guillotina/.well-known/oauth-protected-resource")
        assert status == 200
        assert response["resource"].endswith("/db/guillotina/@mcp/protocol")
        assert response["authorization_servers"][0].endswith("/db/guillotina")
        assert response["scopes_supported"] == ["guillotina:access"]

        response, status = await requester(
            "GET", "/.well-known/oauth-protected-resource/db/guillotina/@mcp/protocol"
        )
        assert status == 200
        assert response["resource"].endswith("/db/guillotina/@mcp/protocol")


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_mcp_without_token_challenges(container_install_requester):
    async with container_install_requester as requester:
        _value, status, headers = await requester.make_request(
            "POST",
            "/db/guillotina/@mcp/protocol",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            headers=PROTOCOL_HEADERS,
            authenticated=False,
        )
        assert status == 401
        www_authenticate = headers["WWW-Authenticate"]
        assert "resource_metadata" in www_authenticate
        assert "/.well-known/oauth-protected-resource/db/guillotina/@mcp/protocol" in www_authenticate
        assert 'scope="guillotina:access"' in www_authenticate


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_mcp_allows_non_oauth_guillotina_authentication(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/@mcp/protocol",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}),
            headers=PROTOCOL_HEADERS,
        )
        _skip_if_protocol_unavailable(response, status)
        assert status == 200


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_mcp_with_oauth_token(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(
            requester, client, resource="http://localhost/db/guillotina/@mcp/protocol"
        )
        token = await token_from_code(requester, client, code, verifier)
        response, status = await requester(
            "POST",
            "/db/guillotina/@mcp/protocol",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}),
            headers=PROTOCOL_HEADERS,
            auth_type="Bearer",
            token=token["access_token"],
        )
        _skip_if_protocol_unavailable(response, status)
        assert status == 200


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_authorize_get_preserves_multiple_resource_parameters(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        verifier, challenge = verifier_pair()
        params = [
            ("response_type", "code"),
            ("client_id", client["client_id"]),
            ("redirect_uri", client["redirect_uris"][0]),
            ("scope", "guillotina:access"),
            ("state", "abc"),
            ("resource", "http://localhost/db/guillotina"),
            ("resource", "http://localhost/db/guillotina/@mcp/protocol"),
            ("code_challenge", challenge),
            ("code_challenge_method", "S256"),
        ]
        value, status, _headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params=params,
            allow_redirects=False,
        )
        assert status == 200
        body = value.decode("utf-8") if isinstance(value, bytes) else value
        assert body.count('name="resource"') == 2

        post_params = params + [
            ("oauth_csrf", oauth_csrf_from_body(value)),
            ("decision", "allow"),
        ]
        _value, status, headers = await requester.make_request(
            "POST",
            "/db/guillotina/oauth/authorize",
            data=urlencode(post_params),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
        )
        assert status == 302

        code = parse_qs(urlparse(headers["Location"]).query)["code"][0]
        token = await token_from_code(requester, client, code, verifier)
        claims = jwt.decode(
            token["access_token"],
            access_token_signing_key(),
            algorithms=[app_settings["jwt"]["algorithm"]],
            options={"verify_aud": False},
        )
        assert set(claims["aud"]) == {
            "http://localhost/db/guillotina",
            "http://localhost/db/guillotina/@mcp/protocol",
        }


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_mcp_rejects_missing_mcp_audience(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client, resource="http://localhost/db/guillotina")
        token = await token_from_code(requester, client, code, verifier)
        _response, status, headers = await requester.make_request(
            "POST",
            "/db/guillotina/@mcp/protocol",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}),
            headers=PROTOCOL_HEADERS,
            auth_type="Bearer",
            token=token["access_token"],
        )
        assert status == 401
        assert 'error="invalid_token"' in headers["WWW-Authenticate"]


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_mcp_search_with_read_only_token(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(
            requester,
            client,
            resource="http://localhost/db/guillotina/@mcp/protocol",
        )
        token = await token_from_code(requester, client, code, verifier)
        response, status = await requester(
            "POST",
            "/db/guillotina/@mcp/protocol",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "search", "arguments": {"query": {}}},
                }
            ),
            headers=PROTOCOL_HEADERS,
            auth_type="Bearer",
            token=token["access_token"],
        )
        _skip_if_protocol_unavailable(response, status)
        assert status == 200


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_mcp_serialized_content_with_oauth_token(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(
            requester,
            client,
            resource="http://localhost/db/guillotina/@mcp/protocol",
        )
        token = await token_from_code(requester, client, code, verifier)
        response, status = await requester(
            "POST",
            "/db/guillotina/@mcp/protocol",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "resolve_path",
                        "arguments": {"path": "/", "include_serialized": True},
                    },
                }
            ),
            headers=PROTOCOL_HEADERS,
            auth_type="Bearer",
            token=token["access_token"],
        )
        _skip_if_protocol_unavailable(response, status)
        assert status == 200


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_subresource_mcp_unauthorized(container_install_requester):
    async with container_install_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps({"@type": "Folder", "id": "subfolder", "title": "Subfolder"}),
        )
        assert status == 201

        _value, status, headers = await requester.make_request(
            "POST",
            "/db/guillotina/subfolder/@mcp/protocol",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            headers=PROTOCOL_HEADERS,
            authenticated=False,
        )
        assert status == 401
        www_authenticate = headers["WWW-Authenticate"]
        assert "resource_metadata" in www_authenticate
        assert (
            "/.well-known/oauth-protected-resource/db/guillotina/subfolder/@mcp/protocol" in www_authenticate
        )

        response, status = await requester(
            "GET", "/.well-known/oauth-protected-resource/db/guillotina/subfolder/@mcp/protocol"
        )
        assert status == 200
        assert response["resource"].endswith("/db/guillotina/subfolder/@mcp/protocol")


@pytest.mark.app_settings(OAUTH_MCP_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth", "mcp"]])
async def test_subresource_mcp_authorized(container_install_requester):
    async with container_install_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps({"@type": "Folder", "id": "subfolder", "title": "Subfolder"}),
        )
        assert status == 201

        client = await register_client(requester)
        code, verifier = await authorize_code(
            requester, client, resource="http://localhost/db/guillotina/subfolder/@mcp/protocol"
        )
        token = await token_from_code(requester, client, code, verifier)

        response, status = await requester(
            "POST",
            "/db/guillotina/subfolder/@mcp/protocol",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}),
            headers=PROTOCOL_HEADERS,
            auth_type="Bearer",
            token=token["access_token"],
        )
        _skip_if_protocol_unavailable(response, status)
        assert status == 200
