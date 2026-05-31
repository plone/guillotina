import json

import pytest

from guillotina.tests.oauth.conftest import OAUTH_SETTINGS, requires_pg


pytestmark = [pytest.mark.asyncio, requires_pg]


RATE_LIMITED_SETTINGS = {
    **OAUTH_SETTINGS,
    "oauth": {"registration_rate_limit": 2, "registration_rate_window": 600},
}


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_register_client(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/oauth/register",
            data=json.dumps({"client_name": "Example", "redirect_uris": ["http://127.0.0.1:12345/callback"]}),
            authenticated=False,
        )
        assert status == 200
        assert response["client_id"]
        assert response["token_endpoint_auth_method"] == "none"


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize(
    "payload",
    [
        {"redirect_uris": []},
        {"redirect_uris": ["javascript:alert(1)"]},
        {"redirect_uris": ["https://example.com/*"]},
        {"redirect_uris": ["https://example.com/cb#fragment"]},
        {"redirect_uris": ["http://example.com/callback"]},
        {"redirect_uris": ["http://localhost/cb"], "token_endpoint_auth_method": "client_secret_basic"},
        {"redirect_uris": ["http://localhost/cb"], "grant_types": ["implicit"]},
        {"redirect_uris": ["http://localhost/cb"], "response_types": ["token"]},
    ],
)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_register_rejects_invalid(payload, container_install_requester):
    async with container_install_requester as requester:
        _response, status = await requester("POST", "/db/guillotina/oauth/register", data=json.dumps(payload))
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_register_accepts_loopback(container_install_requester):
    async with container_install_requester as requester:
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/register",
            data=json.dumps({"redirect_uris": ["http://localhost:9999/callback"]}),
        )
        assert status == 200


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_register_accepts_cursor_native_redirect(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/oauth/register",
            data=json.dumps(
                {
                    "client_name": "Cursor",
                    "redirect_uris": ["cursor://anysphere.cursor-mcp/oauth/callback"],
                }
            ),
            authenticated=False,
        )
        assert status == 200
        assert response["redirect_uris"] == ["cursor://anysphere.cursor-mcp/oauth/callback"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_register_accepts_multiple_redirect_uris(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/oauth/register",
            data=json.dumps(
                {
                    "client_name": "Cursor",
                    "redirect_uris": [
                        "cursor://anysphere.cursor-mcp/oauth/callback",
                        "https://www.cursor.com/agents/mcp/oauth/callback",
                        "http://localhost:8787/callback",
                    ],
                }
            ),
            authenticated=False,
        )
        assert status == 200
        assert response["redirect_uris"] == [
            "cursor://anysphere.cursor-mcp/oauth/callback",
            "https://www.cursor.com/agents/mcp/oauth/callback",
            "http://localhost:8787/callback",
        ]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_register_rejects_client_supplied_client_id(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/oauth/register",
            data=json.dumps(
                {
                    "client_id": "cursor",
                    "client_name": "Cursor",
                    "redirect_uris": ["cursor://anysphere.cursor-mcp/oauth/callback"],
                }
            ),
            authenticated=False,
        )
        assert status == 400
        assert response["error"] == "invalid_request"
        assert response["error_description"] == "client_id is server-issued"


@pytest.mark.app_settings(RATE_LIMITED_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_register_rate_limited(container_install_requester):
    from guillotina.contrib.oauth.flow.ratelimit import reset_rate_limits

    reset_rate_limits()
    payload = json.dumps({"redirect_uris": ["http://localhost:9999/callback"]})
    async with container_install_requester as requester:
        for _ in range(2):
            _response, status = await requester(
                "POST", "/db/guillotina/oauth/register", data=payload, authenticated=False
            )
            assert status == 200
        response, status = await requester(
            "POST", "/db/guillotina/oauth/register", data=payload, authenticated=False
        )
        assert status == 429
        assert response["error"] == "temporarily_unavailable"
    reset_rate_limits()
