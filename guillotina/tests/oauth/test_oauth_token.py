import jwt
import pytest

from guillotina import app_settings
from guillotina.tests.oauth.conftest import OAUTH_SETTINGS, authorize_code, register_client, token_from_code

pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_code_token_and_refresh_rotation(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client, resource="http://localhost/db/guillotina")
        token = await token_from_code(requester, client, code, verifier)
        claims = jwt.decode(token["access_token"], app_settings["jwt"]["secret"], algorithms=[app_settings["jwt"]["algorithm"]], options={"verify_aud": False})
        assert claims["iss"].endswith("/db/guillotina")
        assert claims["sub"] == claims["id"]
        assert claims["client_id"] == client["client_id"]
        assert claims["scope"] == "guillotina:mcp.read"
        assert claims["aud"]
        _response, status = await requester("POST", "/db/guillotina/oauth/token", data=f"grant_type=authorization_code&client_id={client['client_id']}&redirect_uri={client['redirect_uris'][0]}&code={code}&code_verifier={verifier}")
        assert status == 400
        refreshed, status = await requester("POST", "/db/guillotina/oauth/token", data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={token['refresh_token']}")
        assert status == 200
        assert refreshed["refresh_token"] != token["refresh_token"]
        _response, status = await requester("POST", "/db/guillotina/oauth/token", data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={token['refresh_token']}")
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_token_rejects_bad_pkce_and_redirect(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client)
        _response, status = await requester("POST", "/db/guillotina/oauth/token", data=f"grant_type=authorization_code&client_id={client['client_id']}&redirect_uri={client['redirect_uris'][0]}&code={code}&code_verifier=bad")
        assert status == 400
        code, verifier = await authorize_code(requester, client, scope="guillotina:mcp.read guillotina:mcp.search")
        _response, status = await requester("POST", "/db/guillotina/oauth/token", data=f"grant_type=authorization_code&client_id={client['client_id']}&redirect_uri=http://127.0.0.1:9999/cb&code={code}&code_verifier={verifier}")
        assert status == 400
