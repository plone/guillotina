import copy

import pytest

from guillotina.tests.oauth.conftest import OAUTH_SETTINGS, requires_pg


pytestmark = [pytest.mark.asyncio, requires_pg]


OAUTH_SETTINGS_TRUST_PROXY = copy.deepcopy(OAUTH_SETTINGS)
OAUTH_SETTINGS_TRUST_PROXY["oauth"]["trust_proxy_headers"] = True


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_metadata(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester("GET", "/db/guillotina/.well-known/oauth-authorization-server")
        assert status == 200
        assert response["issuer"].endswith("/db/guillotina")
        assert response["authorization_endpoint"].endswith("/oauth/authorize")
        assert response["registration_endpoint"].endswith("/oauth/register")
        assert response["revocation_endpoint_auth_methods_supported"] == ["none"]
        assert response["resource_indicators_supported"] is True


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


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_metadata_ignores_forwarded_proto_by_default(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester(
            "GET",
            "/db/guillotina/.well-known/oauth-authorization-server",
            headers={"X-Forwarded-Proto": "https"},
        )
        assert status == 200
        # Secure default: spoofable forwarding header must not promote issuer to https
        assert response["issuer"].startswith("http://")
        assert response["authorization_endpoint"].startswith("http://")


@pytest.mark.app_settings(OAUTH_SETTINGS_TRUST_PROXY)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_metadata_trusts_forwarded_proto_when_enabled(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester(
            "GET",
            "/db/guillotina/.well-known/oauth-authorization-server",
            headers={"X-Forwarded-Proto": "https"},
        )
        assert status == 200
        # Opt-in: behind a trusted reverse proxy the forwarded scheme is honored
        assert response["issuer"].startswith("https://")
