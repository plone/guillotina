import pytest

from guillotina.tests.oauth.conftest import OAUTH_SETTINGS, authorize_code, register_client, token_from_code

pytestmark = pytest.mark.asyncio


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
        )
        assert status == 200
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={token['refresh_token']}",
        )
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_revoke_unknown_token(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _response, status = await requester(
            "POST", "/db/guillotina/oauth/revoke", data=f"client_id={client['client_id']}&token=unknown"
        )
        assert status == 200
