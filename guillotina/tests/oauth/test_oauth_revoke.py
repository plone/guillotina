import pytest

from guillotina.contrib.oauth.utils.ratelimit import reset_rate_limits
from guillotina.tests.oauth.conftest import (
    OAUTH_SETTINGS,
    authorize_code,
    register_client,
    requires_pg,
    token_from_code,
)


pytestmark = [pytest.mark.asyncio, requires_pg]

REVOKE_RATE_LIMIT_SETTINGS = {
    **OAUTH_SETTINGS,
    "oauth": {**OAUTH_SETTINGS["oauth"], "revoke_rate_limit": 2, "revoke_rate_window": 300},
}


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_revoke_refresh_token(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client)
        token = await token_from_code(requester, client, code, verifier)
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/revoke",
            data=f"client_id={client['client_id']}&token={token['refresh_token']}&token_type_hint=refresh_token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 200
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={token['refresh_token']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_revoke_rotated_refresh_token_revokes_family(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client)
        token = await token_from_code(requester, client, code, verifier)
        rotated, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={token['refresh_token']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 200

        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/revoke",
            data=f"client_id={client['client_id']}&token={token['refresh_token']}&token_type_hint=refresh_token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 200

        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={rotated['refresh_token']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_revoke_does_not_cross_authorization_grants(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code_a, verifier_a = await authorize_code(requester, client)
        token_a = await token_from_code(requester, client, code_a, verifier_a)
        code_b, verifier_b = await authorize_code(requester, client)
        token_b = await token_from_code(requester, client, code_b, verifier_b)

        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/revoke",
            data=f"client_id={client['client_id']}&token={token_a['refresh_token']}&token_type_hint=refresh_token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 200

        refreshed_b, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={token_b['refresh_token']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 200
        assert refreshed_b["refresh_token"] != token_b["refresh_token"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_revoke_unknown_token(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/revoke",
            data=f"client_id={client['client_id']}&token=unknown",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 200


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_revoke_requires_form_content_type(container_install_requester):
    async with container_install_requester as requester:
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/revoke",
            data="client_id=client&token=token",
            headers={"Content-Type": "text/plain"},
        )
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_revoke_requires_token(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        response, status = await requester(
            "POST",
            "/db/guillotina/oauth/revoke",
            data=f"client_id={client['client_id']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400
        assert response["error"] == "invalid_request"


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_revoke_reports_unsupported_access_token_revocation(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        response, status = await requester(
            "POST",
            "/db/guillotina/oauth/revoke",
            data=f"client_id={client['client_id']}&token=token&token_type_hint=access_token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400
        assert response["error"] == "unsupported_token_type"


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_revoke_rejects_duplicate_singleton_parameter(container_install_requester):
    async with container_install_requester as requester:
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/revoke",
            data="client_id=client&client_id=client&token=token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400


@pytest.mark.app_settings(REVOKE_RATE_LIMIT_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_revoke_endpoint_rate_limited(container_install_requester):
    reset_rate_limits()
    async with container_install_requester as requester:
        client = await register_client(requester)
        body = f"client_id={client['client_id']}&token=unknown"

        async def _attempt():
            response, status = await requester(
                "POST",
                "/db/guillotina/oauth/revoke",
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            return response, status

        _response, status = await _attempt()
        assert status == 200
        _response, status = await _attempt()
        assert status == 200
        response, status = await _attempt()
        assert status == 429
        assert response["error"] == "temporarily_unavailable"
    reset_rate_limits()
