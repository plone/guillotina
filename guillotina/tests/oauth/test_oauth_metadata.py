import pytest

from guillotina.tests.oauth.conftest import OAUTH_SETTINGS

pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_metadata(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester("GET", "/db/guillotina/.well-known/oauth-authorization-server")
        assert status == 200
        assert response["issuer"].endswith("/db/guillotina")
        assert response["authorization_endpoint"].endswith("/oauth/authorize")
        assert response["registration_endpoint"].endswith("/oauth/register")


@pytest.mark.app_settings(OAUTH_SETTINGS)
async def test_metadata_requires_addon(container_requester):
    async with container_requester as requester:
        _response, status = await requester("GET", "/db/guillotina/.well-known/oauth-authorization-server")
        assert status == 412
