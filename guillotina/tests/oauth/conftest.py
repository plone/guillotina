import base64
import hashlib
from html import unescape
import json
import re
from urllib.parse import parse_qs, urlencode, urlparse

import pytest

from guillotina.tests.fixtures import annotations


pytestmark = pytest.mark.asyncio

requires_pg = pytest.mark.skipif(
    annotations["testdatabase"] == "DUMMY",
    reason="requires PostgreSQL (set DATABASE=postgresql)",
)

OAUTH_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.oauth"],
    "oauth": {"registration_rate_limit": 0},
    "auth_extractors": [
        "guillotina.auth.extractors.BearerAuthPolicy",
        "guillotina.auth.extractors.BasicAuthPolicy",
        "guillotina.auth.extractors.WSTokenAuthPolicy",
        "guillotina.auth.extractors.CookiePolicy",
    ],
}
OAUTH_MCP_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.oauth", "guillotina.contrib.mcp"],
    "oauth": {"registration_rate_limit": 0},
    "auth_extractors": [
        "guillotina.auth.extractors.BearerAuthPolicy",
        "guillotina.auth.extractors.BasicAuthPolicy",
        "guillotina.auth.extractors.WSTokenAuthPolicy",
        "guillotina.auth.extractors.CookiePolicy",
    ],
}


def verifier_pair(verifier="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"):
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def oauth_csrf_from_body(value):
    body = value.decode("utf-8") if isinstance(value, bytes) else value
    match = re.search(r'name="oauth_csrf" value="([^"]+)"', body)
    assert match is not None, body
    return unescape(match.group(1))


async def register_client(requester, redirect_uri="http://127.0.0.1:12345/callback"):
    response, status = await requester(
        "POST",
        "/db/guillotina/oauth/register",
        data=json.dumps(
            {
                "client_name": "Test",
                "redirect_uris": [redirect_uri],
                "scope": "guillotina:access",
            }
        ),
    )
    assert status == 200
    return response


async def authorize_code(
    requester,
    client,
    *,
    scope="guillotina:access",
    resource=None,
    verifier="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
):
    verifier, challenge = verifier_pair(verifier)
    data = {
        "response_type": "code",
        "client_id": client["client_id"],
        "redirect_uri": client["redirect_uris"][0],
        "scope": scope,
        "state": "abc",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if resource:
        data["resource"] = resource

    value, status, headers = await requester.make_request(
        "GET",
        "/db/guillotina/oauth/authorize",
        params=data,
        allow_redirects=False,
    )
    if status == 302:
        query = parse_qs(urlparse(headers["Location"]).query)
        return query["code"][0], verifier
    assert status == 200

    data["oauth_csrf"] = oauth_csrf_from_body(value)
    data["decision"] = "allow"
    value, status, headers = await requester.make_request(
        "POST",
        "/db/guillotina/oauth/authorize",
        data=urlencode(data),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        allow_redirects=False,
    )
    assert status == 302
    query = parse_qs(urlparse(headers["Location"]).query)
    return query["code"][0], verifier


async def token_from_code(requester, client, code, verifier):
    body = urlencode(
        {
            "grant_type": "authorization_code",
            "client_id": client["client_id"],
            "redirect_uri": client["redirect_uris"][0],
            "code": code,
            "code_verifier": verifier,
        }
    )
    response, status = await requester(
        "POST",
        "/db/guillotina/oauth/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert status == 200, response
    return response
