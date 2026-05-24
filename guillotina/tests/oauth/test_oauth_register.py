import json

import pytest

from guillotina.tests.oauth.conftest import OAUTH_SETTINGS

pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_register_client(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester("POST", "/db/guillotina/oauth/register", data=json.dumps({"client_name": "Example", "redirect_uris": ["http://127.0.0.1:12345/callback"]}))
        assert status == 200
        assert response["client_id"]
        assert response["token_endpoint_auth_method"] == "none"


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("payload", [
    {"redirect_uris": []},
    {"redirect_uris": ["javascript:alert(1)"]},
    {"redirect_uris": ["https://example.com/*"]},
    {"redirect_uris": ["http://localhost/cb"], "token_endpoint_auth_method": "client_secret_basic"},
])
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_register_rejects_invalid(payload, container_install_requester):
    async with container_install_requester as requester:
        _response, status = await requester("POST", "/db/guillotina/oauth/register", data=json.dumps(payload))
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_register_accepts_loopback(container_install_requester):
    async with container_install_requester as requester:
        _response, status = await requester("POST", "/db/guillotina/oauth/register", data=json.dumps({"redirect_uris": ["http://localhost:9999/callback"]}))
        assert status == 200
