import pytest

from guillotina.tests.oauth.conftest import OAUTH_SETTINGS, requires_pg


pytestmark = [pytest.mark.asyncio, requires_pg]


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
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_rfc_metadata(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester("GET", "/.well-known/oauth-authorization-server/db/guillotina")
        assert status == 200
        assert response["issuer"].endswith("/db/guillotina")
        assert response["authorization_endpoint"].endswith("/oauth/authorize")

        response, status = await requester("GET", "/.well-known/openid-configuration/db/guillotina")
        assert status == 200
        assert response["issuer"].endswith("/db/guillotina")


@pytest.mark.app_settings(OAUTH_SETTINGS)
async def test_metadata_requires_addon(container_requester):
    async with container_requester as requester:
        _response, status = await requester("GET", "/db/guillotina/.well-known/oauth-authorization-server")
        assert status == 412
