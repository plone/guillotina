import json
from urllib.parse import parse_qs, urlencode, urlparse

import pytest

from guillotina.tests.oauth.conftest import (
    OAUTH_SETTINGS,
    oauth_csrf_from_body,
    register_client,
    requires_pg,
    verifier_pair,
)


pytestmark = [pytest.mark.asyncio, requires_pg]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_unknown_client(container_install_requester):
    async with container_install_requester as requester:
        _response, status = await requester(
            "GET", "/db/guillotina/oauth/authorize", params={"client_id": "missing"}
        )
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_accepts_cursor_redirect_registered_with_client(container_install_requester):
    async with container_install_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/oauth/register",
            data=json.dumps(
                {
                    "client_name": "Cursor",
                    "redirect_uris": [
                        "http://127.0.0.1:12345/callback",
                        "cursor://anysphere.cursor-mcp/oauth/callback",
                    ],
                }
            ),
            headers={"Content-Type": "application/json"},
            authenticated=False,
        )
        assert status == 201
        client = response
        _response, status = await requester(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": "cursor://anysphere.cursor-mcp/oauth/callback",
                "response_type": "code",
                "code_challenge": verifier_pair()[1],
                "code_challenge_method": "S256",
                "scope": "guillotina:access",
            },
        )
        assert status == 200
        body = _response.decode("utf-8") if isinstance(_response, bytes) else _response
        assert "Login" in body or "Allow" in body


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_accepts_loopback_redirect_with_different_port(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester, redirect_uri="http://127.0.0.1:12345/callback")
        _response, status = await requester(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": "http://127.0.0.1:54321/callback",
                "response_type": "code",
                "code_challenge": verifier_pair()[1],
                "code_challenge_method": "S256",
                "scope": "guillotina:access",
            },
        )
        assert status == 200


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_consent_page_describes_requested_access(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        value, status, _headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": client["redirect_uris"][0],
                "response_type": "code",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "guillotina:access",
            },
            allow_redirects=False,
        )
        body = value.decode("utf-8")
        assert status == 200
        assert "Allow Test" in body
        assert "Requested permissions" in body
        assert "Access Guillotina on behalf" in body
        assert "Resources this client can access" in body
        assert client["redirect_uris"][0] in body


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_register_rejects_client_supplied_client_id(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester, redirect_uri="http://127.0.0.1:12345/callback")
        response, status = await requester(
            "POST",
            "/db/guillotina/oauth/register",
            data=json.dumps(
                {
                    "client_id": client["client_id"],
                    "client_name": "Cursor",
                    "redirect_uris": ["cursor://anysphere.cursor-mcp/oauth/callback"],
                }
            ),
            headers={"Content-Type": "application/json"},
            authenticated=False,
        )
        assert status == 400
        assert response["error"] == "invalid_request"
        assert response["error_description"] == "client_id is server-issued"


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_bad_redirect_does_not_redirect(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _response, status = await requester(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": "https://evil.example/cb",
                "response_type": "code",
            },
        )
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("challenge_method", [None, "plain"])
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_pkce_required(challenge_method, container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        data = {
            "client_id": client["client_id"],
            "redirect_uri": client["redirect_uris"][0],
            "response_type": "code",
        }
        if challenge_method:
            data.update({"code_challenge": "x", "code_challenge_method": challenge_method})
        _value, status, headers = await requester.make_request(
            "GET", "/db/guillotina/oauth/authorize", params=data, allow_redirects=False
        )
        assert status == 302
        assert "error=invalid_request" in headers["Location"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_rejects_invalid_code_challenge(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _value, status, headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": client["redirect_uris"][0],
                "response_type": "code",
                "scope": "guillotina:access",
                "code_challenge": "short",
                "code_challenge_method": "S256",
            },
            allow_redirects=False,
        )
        assert status == 302
        assert "error=invalid_request" in headers["Location"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_rejects_duplicate_singleton_parameter(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        _value, status, headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params=[
                ("client_id", client["client_id"]),
                ("client_id", client["client_id"]),
                ("redirect_uri", client["redirect_uris"][0]),
                ("response_type", "code"),
                ("scope", "guillotina:access"),
                ("code_challenge", challenge),
                ("code_challenge_method", "S256"),
            ],
            allow_redirects=False,
        )
        assert status == 400


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_allow_and_remember_consent(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        params = {
            "response_type": "code",
            "client_id": client["client_id"],
            "redirect_uri": client["redirect_uris"][0],
            "scope": "guillotina:access",
            "state": "s",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        value, status, _headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params=params,
            allow_redirects=False,
        )
        assert status == 200
        params["oauth_csrf"] = oauth_csrf_from_body(value)
        params["decision"] = "allow"
        _value, status, headers = await requester.make_request(
            "POST",
            "/db/guillotina/oauth/authorize",
            data=urlencode(params),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
        )
        assert status == 302
        query = parse_qs(urlparse(headers["Location"]).query)
        assert query["code"][0]
        assert query["state"][0] == "s"
        _value, status, _headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": client["client_id"],
                "redirect_uri": client["redirect_uris"][0],
                "scope": "guillotina:access",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
            allow_redirects=False,
        )
        assert status == 302


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_deny(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        params = {
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
            params=params,
            allow_redirects=False,
        )
        assert status == 200
        params["oauth_csrf"] = oauth_csrf_from_body(value)
        params["decision"] = "deny"
        _value, status, headers = await requester.make_request(
            "POST",
            "/db/guillotina/oauth/authorize",
            data=urlencode(params),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
        )
        assert status == 302
        assert "error=access_denied" in headers["Location"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_get_decision_allow_does_not_create_code(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        value, status, _headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": client["client_id"],
                "redirect_uri": client["redirect_uris"][0],
                "scope": "guillotina:access",
                "state": "s",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "decision": "allow",
            },
            allow_redirects=False,
        )
        assert status == 200
        body = value.decode("utf-8") if isinstance(value, bytes) else value
        assert "Allow Test" in body
        assert "code=" not in body


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_post_decision_requires_csrf(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        body = (
            "response_type=code"
            f"&client_id={client['client_id']}"
            f"&redirect_uri={client['redirect_uris'][0]}"
            "&scope=guillotina:access&state=s"
            f"&code_challenge={challenge}"
            "&code_challenge_method=S256&decision=allow"
        )
        _value, status, headers = await requester.make_request(
            "POST",
            "/db/guillotina/oauth/authorize",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
        )
        assert status == 302
        assert "error=invalid_request" in headers["Location"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_invalid_response_type_redirects(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _value, status, headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": client["redirect_uris"][0],
                "response_type": "token",
            },
            allow_redirects=False,
        )
        assert status == 302
        assert "error=unsupported_response_type" in headers["Location"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_invalid_scope_redirects(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        _value, status, headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": client["redirect_uris"][0],
                "response_type": "code",
                "scope": "unsupported_scope",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
            allow_redirects=False,
        )
        assert status == 302
        assert "error=invalid_scope" in headers["Location"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_without_scope(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        _value, status, headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": client["redirect_uris"][0],
                "response_type": "code",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
            allow_redirects=False,
        )
        assert status == 302
        assert "error=invalid_scope" in headers["Location"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_invalid_target_redirects(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        _value, status, headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": client["redirect_uris"][0],
                "response_type": "code",
                "scope": "guillotina:access",
                "resource": "http://invalid-target.com",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
            allow_redirects=False,
        )
        assert status == 302
        assert "error=invalid_target" in headers["Location"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_oauth_only_rejects_mcp_protocol_resource(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        _value, status, headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": client["redirect_uris"][0],
                "response_type": "code",
                "scope": "guillotina:access",
                "resource": "http://localhost/db/guillotina/@mcp/protocol",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
            allow_redirects=False,
        )
        assert status == 302
        assert "error=invalid_target" in headers["Location"]


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_sets_auth_token_cookie(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        body = (
            "response_type=code"
            f"&client_id={client['client_id']}"
            f"&redirect_uri={client['redirect_uris'][0]}"
            "&scope=guillotina:access"
            f"&code_challenge={challenge}"
            "&code_challenge_method=S256"
            "&username=root&password=admin&decision=allow"
        )
        _value, status, headers = await requester.make_request(
            "POST",
            "/db/guillotina/oauth/authorize",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            authenticated=False,
            allow_redirects=False,
        )
        assert status == 200
        assert "Set-Cookie" in headers
        assert "auth_token=" in headers["Set-Cookie"]
        assert b"Allow Test" in _value


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_cookie_authenticates_get_request(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()

        # 1. First authenticate with POST login to get the auth_token cookie
        body = (
            "response_type=code"
            f"&client_id={client['client_id']}"
            f"&redirect_uri={client['redirect_uris'][0]}"
            "&scope=guillotina:access"
            f"&code_challenge={challenge}"
            "&code_challenge_method=S256"
            "&username=root&password=admin"
        )
        _value, status, headers = await requester.make_request(
            "POST",
            "/db/guillotina/oauth/authorize",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            authenticated=False,
            allow_redirects=False,
        )
        assert "Set-Cookie" in headers
        cookie_header = headers["Set-Cookie"]
        assert "auth_token=" in cookie_header

        # Extract cookie value
        cookie_token = cookie_header.split(";")[0].split("=")[1]

        # 2. Make a GET request with the extracted cookie (authenticated=False so no basic auth is sent)
        # It should bypass login and show the consent form (status 200) instead of prompting for login again!
        value, status, headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": client["client_id"],
                "redirect_uri": client["redirect_uris"][0],
                "scope": "guillotina:access",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
            headers={"Cookie": f"auth_token={cookie_token}"},
            authenticated=False,
            allow_redirects=False,
        )
        assert status == 200
        assert b"Allow Test" in value


OAUTH_LOGIN_LIMIT_SETTINGS = {
    **OAUTH_SETTINGS,
    "oauth": {**OAUTH_SETTINGS["oauth"], "login_rate_limit": 2, "login_rate_window": 300},
}
OAUTH_EXTRA_SCOPE_SETTINGS = {
    **OAUTH_SETTINGS,
    "oauth": {**OAUTH_SETTINGS["oauth"], "scopes_supported": ["guillotina:access", "guillotina:extra"]},
}


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_response_includes_iss(container_install_requester):
    """RFC 9207: the authorization response must carry the issuer identifier."""
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        params = {
            "response_type": "code",
            "client_id": client["client_id"],
            "redirect_uri": client["redirect_uris"][0],
            "scope": "guillotina:access",
            "state": "s",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        value, status, _headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params=params,
            allow_redirects=False,
        )
        assert status == 200
        params["oauth_csrf"] = oauth_csrf_from_body(value)
        params["decision"] = "allow"
        _value, status, headers = await requester.make_request(
            "POST",
            "/db/guillotina/oauth/authorize",
            data=urlencode(params),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
        )
        assert status == 302
        query = parse_qs(urlparse(headers["Location"]).query)
        assert query["code"][0]
        assert query["iss"][0].endswith("/db/guillotina")


@pytest.mark.app_settings(OAUTH_LOGIN_LIMIT_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_login_rate_limited_after_failures(container_install_requester):
    """Failed credential logins at the authorization endpoint are throttled."""
    from guillotina.contrib.oauth.utils.ratelimit import reset_rate_limits

    reset_rate_limits()
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        body = (
            "response_type=code"
            f"&client_id={client['client_id']}"
            f"&redirect_uri={client['redirect_uris'][0]}"
            "&scope=guillotina:access"
            f"&code_challenge={challenge}"
            "&code_challenge_method=S256"
            "&username=root&password=wrong-password"
        )

        async def _attempt():
            _value, status, _headers = await requester.make_request(
                "POST",
                "/db/guillotina/oauth/authorize",
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                authenticated=False,
                allow_redirects=False,
            )
            return status

        assert await _attempt() == 401
        assert await _attempt() == 401
        # Third failed attempt is blocked by the sliding-window limiter.
        assert await _attempt() == 429
        reset_rate_limits()


@pytest.mark.app_settings(OAUTH_EXTRA_SCOPE_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_authorize_rejects_scope_not_registered_for_client(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        _verifier, challenge = verifier_pair()
        _value, status, headers = await requester.make_request(
            "GET",
            "/db/guillotina/oauth/authorize",
            params={
                "client_id": client["client_id"],
                "redirect_uri": client["redirect_uris"][0],
                "response_type": "code",
                "scope": "guillotina:access guillotina:extra",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
            allow_redirects=False,
        )
        assert status == 302
        assert "error=invalid_scope" in headers["Location"]
