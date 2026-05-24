import base64
import hashlib
import json
from urllib.parse import parse_qs, urlparse

import pytest


pytestmark = pytest.mark.asyncio

OAUTH_SETTINGS = {"applications": ["guillotina", "guillotina.contrib.oauth"]}
OAUTH_MCP_SETTINGS = {"applications": ["guillotina", "guillotina.contrib.oauth", "guillotina.contrib.mcp"]}


def verifier_pair(verifier="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"):
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


async def register_client(requester, redirect_uri="http://127.0.0.1:12345/callback"):
    response, status = await requester(
        "POST",
        "/db/guillotina/oauth/register",
        data=json.dumps({"client_name": "Test", "redirect_uris": [redirect_uri], "scope": "guillotina:mcp.read guillotina:mcp.search"}),
    )
    assert status == 200
    return response


async def authorize_code(requester, client, *, scope="guillotina:mcp.read", resource=None, verifier="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"):
    verifier, challenge = verifier_pair(verifier)
    data = {
        "response_type": "code",
        "client_id": client["client_id"],
        "redirect_uri": client["redirect_uris"][0],
        "scope": scope,
        "state": "abc",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "decision": "allow",
    }
    if resource:
        data["resource"] = resource
    value, status, headers = await requester.make_request(
        "POST",
        "/db/guillotina/oauth/authorize",
        data="&".join(f"{k}={v}" for k, v in data.items()),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        allow_redirects=False,
    )
    assert status == 302
    query = parse_qs(urlparse(headers["Location"]).query)
    return query["code"][0], verifier


async def token_from_code(requester, client, code, verifier):
    body = (
        f"grant_type=authorization_code&client_id={client['client_id']}&redirect_uri={client['redirect_uris'][0]}"
        f"&code={code}&code_verifier={verifier}"
    )
    response, status = await requester(
        "POST",
        "/db/guillotina/oauth/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert status == 200
    return response
