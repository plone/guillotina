import pytest

from guillotina.tests.oauth.conftest import OAUTH_SETTINGS, authorize_code, register_client, token_from_code

pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_oauth_access_token_authenticates(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client, resource="http://localhost/db/guillotina")
        token = await token_from_code(requester, client, code, verifier)
        response, status = await requester("GET", "/db/guillotina/@addons", authenticated=True, auth_type="Bearer", token=token["access_token"])
        assert status == 200
        assert "oauth" in response["installed"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_oauth_access_token_wrong_audience_fails_generic_api(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client, resource="http://localhost/db/guillotina/@mcp/protocol")
        token = await token_from_code(requester, client, code, verifier)
        _response, status = await requester("GET", "/db/guillotina/@addons", authenticated=True, auth_type="Bearer", token=token["access_token"])
        assert status in (401, 403)
