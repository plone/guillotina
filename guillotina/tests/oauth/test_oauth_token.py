import jwt
import pytest
from guillotina import app_settings
from guillotina.contrib.oauth.flow.ratelimit import reset_rate_limits
from guillotina.contrib.oauth.flow.tokens import access_token_key
from guillotina.tests.oauth.conftest import (
    OAUTH_SETTINGS,
    authorize_code,
    oauth_csrf_from_body,
    register_client,
    requires_pg,
    token_from_code,
)


pytestmark = [pytest.mark.asyncio, requires_pg]

EXPIRED_CODE_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.oauth"],
    "oauth": {"authorization_code_ttl": 0},
}
EXPIRED_REFRESH_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.oauth"],
    "oauth": {"refresh_token_ttl": 0},
}
TOKEN_RATE_LIMIT_SETTINGS = {
    **OAUTH_SETTINGS,
    "oauth": {**OAUTH_SETTINGS["oauth"], "token_rate_limit": 2, "token_rate_window": 300},
}


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_code_token_and_refresh_rotation(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client, resource="http://localhost/db/guillotina")
        token, status, token_headers = await requester.make_request(
            "POST",
            "/db/guillotina/oauth/token",
            data=(
                "grant_type=authorization_code"
                f"&client_id={client['client_id']}"
                f"&redirect_uri={client['redirect_uris'][0]}"
                f"&code={code}&code_verifier={verifier}"
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
        )
        assert status == 200
        assert token_headers["Cache-Control"] == "no-store"
        assert token_headers["Pragma"] == "no-cache"
        claims = jwt.decode(
            token["access_token"],
            access_token_key(),
            algorithms=[app_settings["jwt"]["algorithm"]],
            options={"verify_aud": False},
        )
        assert claims["iss"].endswith("/db/guillotina")
        assert claims["sub"] == claims["id"]
        assert claims["client_id"] == client["client_id"]
        assert claims["scope"] == "guillotina:access"
        assert claims["aud"]
        refreshed, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={token['refresh_token']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 200
        _refreshed_again, _status, refresh_headers = await requester.make_request(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={refreshed['refresh_token']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
        )
        assert refresh_headers["Cache-Control"] == "no-store"
        assert refresh_headers["Pragma"] == "no-cache"
        assert refreshed["refresh_token"] != token["refresh_token"]
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={token['refresh_token']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_token_rejects_bad_pkce_and_redirect(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client)
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=(
                "grant_type=authorization_code"
                f"&client_id={client['client_id']}"
                f"&redirect_uri={client['redirect_uris'][0]}"
                f"&code={code}&code_verifier=bad"
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400
        code, verifier = await authorize_code(requester, client, scope="guillotina:access")
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=(
                "grant_type=authorization_code"
                f"&client_id={client['client_id']}"
                "&redirect_uri=http://127.0.0.1:9999/cb"
                f"&code={code}&code_verifier={verifier}"
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_token_requires_form_content_type(container_install_requester):
    async with container_install_requester as requester:
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data="grant_type=refresh_token&client_id=client&refresh_token=token",
            headers={"Content-Type": "text/plain"},
        )
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_token_rejects_duplicate_singleton_parameter(container_install_requester):
    async with container_install_requester as requester:
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data="grant_type=refresh_token&grant_type=refresh_token&client_id=client&refresh_token=token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_token_rejects_pkce_verifier_below_min_length(container_install_requester):
    from urllib.parse import parse_qs, urlencode, urlparse

    from guillotina.contrib.oauth.flow.pkce import s256_challenge

    async with container_install_requester as requester:
        client = await register_client(requester)
        verifier_42 = "a" * 42
        challenge = s256_challenge(verifier_42)
        data = {
            "response_type": "code",
            "client_id": client["client_id"],
            "redirect_uri": client["redirect_uris"][0],
            "scope": "guillotina:access",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        value, status, _headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params=data,
            allow_redirects=False,
        )
        assert status == 200
        data["oauth_csrf"] = oauth_csrf_from_body(value)
        data["decision"] = "allow"
        _value, status, headers = await requester.make_request(
            "POST",
            "/db/guillotina/oauth/authorize",
            data=urlencode(data),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
        )
        assert status == 302
        code = parse_qs(urlparse(headers["Location"]).query)["code"][0]

        payload = (
            "grant_type=authorization_code"
            f"&client_id={client['client_id']}"
            f"&redirect_uri={client['redirect_uris'][0]}&code={code}&code_verifier={verifier_42}"
        )
        _resp, tok_status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert tok_status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_refresh_token_reuse_invalidates_rotation_family(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client)
        token_a = await token_from_code(requester, client, code, verifier)

        rotated, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={token_a['refresh_token']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 200
        new_rt = rotated["refresh_token"]

        reused, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={token_a['refresh_token']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400

        _also_bad, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={new_rt}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400


@pytest.mark.app_settings(EXPIRED_CODE_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_expired_authorization_code_fails(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client)
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=(
                f"grant_type=authorization_code&client_id={client['client_id']}"
                f"&redirect_uri={client['redirect_uris'][0]}&code={code}&code_verifier={verifier}"
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400


@pytest.mark.app_settings(EXPIRED_REFRESH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_expired_refresh_token_fails(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client)
        token = await token_from_code(requester, client, code, verifier)
        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={token['refresh_token']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_code_reuse_revokes_tokens(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client, resource="http://localhost/db/guillotina")
        token = await token_from_code(requester, client, code, verifier)
        assert "refresh_token" in token

        _response, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=(
                "grant_type=authorization_code"
                f"&client_id={client['client_id']}"
                f"&redirect_uri={client['redirect_uris'][0]}"
                f"&code={code}&code_verifier={verifier}"
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400

        _refresh_response, status = await requester(
            "POST",
            "/db/guillotina/oauth/token",
            data=f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token={token['refresh_token']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 400


@pytest.mark.app_settings(TOKEN_RATE_LIMIT_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_token_endpoint_rate_limited(container_install_requester):
    reset_rate_limits()
    async with container_install_requester as requester:
        client = await register_client(requester)
        body = f"grant_type=refresh_token&client_id={client['client_id']}&refresh_token=missing"

        async def _attempt():
            response, status = await requester(
                "POST",
                "/db/guillotina/oauth/token",
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            return response, status

        _response, status = await _attempt()
        assert status == 400
        _response, status = await _attempt()
        assert status == 400
        response, status = await _attempt()
        assert status == 429
        assert response["error"] == "temporarily_unavailable"
    reset_rate_limits()
