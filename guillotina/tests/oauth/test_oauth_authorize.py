import json
from urllib.parse import parse_qs, urlparse

import pytest

from guillotina.tests.oauth.conftest import OAUTH_SETTINGS, register_client, verifier_pair

pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_unknown_client(container_install_requester):
    async with container_install_requester as requester:
        _response, status = await requester("GET", "/db/guillotina/oauth/authorize", params={"client_id": "missing"})
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_bad_redirect_does_not_redirect(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _response, status = await requester("GET", "/db/guillotina/oauth/authorize", params={"client_id": client["client_id"], "redirect_uri": "https://evil.example/cb", "response_type": "code"})
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("challenge_method", [None, "plain"])
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_pkce_required(challenge_method, container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        data = {"client_id": client["client_id"], "redirect_uri": client["redirect_uris"][0], "response_type": "code"}
        if challenge_method:
            data.update({"code_challenge": "x", "code_challenge_method": challenge_method})
        _value, status, headers = await requester.make_request("GET", "/db/guillotina/oauth/authorize", params=data, allow_redirects=False)
        assert status == 302
        assert "error=invalid_request" in headers["Location"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_allow_and_remember_consent(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        verifier, challenge = verifier_pair()
        body = f"response_type=code&client_id={client['client_id']}&redirect_uri={client['redirect_uris'][0]}&scope=guillotina:mcp.read&state=s&code_challenge={challenge}&code_challenge_method=S256&decision=allow"
        _value, status, headers = await requester.make_request("POST", "/db/guillotina/oauth/authorize", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, allow_redirects=False)
        assert status == 302
        query = parse_qs(urlparse(headers["Location"]).query)
        assert query["code"][0]
        assert query["state"][0] == "s"
        _value, status, _headers = await requester.make_request("GET", "/db/guillotina/oauth/authorize", params={"response_type": "code", "client_id": client["client_id"], "redirect_uri": client["redirect_uris"][0], "scope": "guillotina:mcp.read", "code_challenge": challenge, "code_challenge_method": "S256"}, allow_redirects=False)
        assert status == 302


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_deny(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        body = f"response_type=code&client_id={client['client_id']}&redirect_uri={client['redirect_uris'][0]}&scope=guillotina:mcp.read&code_challenge={challenge}&code_challenge_method=S256&decision=deny"
        _value, status, headers = await requester.make_request("POST", "/db/guillotina/oauth/authorize", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, allow_redirects=False)
        assert status == 302
        assert "error=access_denied" in headers["Location"]
