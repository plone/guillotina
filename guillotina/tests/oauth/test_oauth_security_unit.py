import jwt
import pytest

from guillotina._settings import app_settings
from guillotina.auth import validators
from guillotina.content import Container
from guillotina.contrib.oauth.api.pages import oauth_error_page
from guillotina.contrib.oauth.auth.validators import OAuthJWTValidator
from guillotina.contrib.oauth.flow.clients import build_client_from_registration, scopes_registered_for_client
from guillotina.contrib.oauth.flow.resources import oauth_required_audience, register_oauth_audience_resolver
from guillotina.contrib.oauth.flow.tokens import issue_access_token
from guillotina.contrib.oauth.utils.ratelimit import rate_limit_check, rate_limit_exceeded, reset_rate_limits
from guillotina.contrib.oauth.utils.urls import container_issuer_url, validate_issuer
from guillotina.response import HTTPBadRequest
from guillotina.tests.utils import make_mocked_request


@pytest.mark.asyncio
@pytest.mark.app_settings({"applications": ["guillotina", "guillotina.contrib.oauth"]})
async def test_oauth_access_token_uses_dedicated_signing_key(dummy_guillotina):
    access_token, _claims = issue_access_token(
        issuer="http://localhost/db/guillotina",
        subject="root",
        audience=["http://localhost/db/guillotina"],
        client_id="client",
        scope=["guillotina:access"],
    )
    with pytest.raises(jwt.exceptions.InvalidSignatureError):
        jwt.decode(
            access_token,
            app_settings["jwt"]["secret"],
            algorithms=[app_settings["jwt"]["algorithm"]],
            options={"verify_aud": False},
        )


@pytest.mark.asyncio
@pytest.mark.app_settings({"applications": ["guillotina", "guillotina.contrib.oauth"]})
async def test_generic_jwt_validator_rejects_oauth_token_type(dummy_guillotina):
    token = jwt.encode(
        {"id": "root", "sub": "root", "token_type": "oauth_access_token"},
        app_settings["jwt"]["secret"],
        algorithm=app_settings["jwt"]["algorithm"],
    )
    assert await validators.JWTValidator().validate({"type": "bearer", "token": token}) is None


@pytest.mark.asyncio
@pytest.mark.app_settings({"applications": ["guillotina", "guillotina.contrib.oauth"]})
@pytest.mark.parametrize("token_type", ["cookie", "wstoken"])
async def test_oauth_access_token_only_accepts_bearer_transport(token_type, dummy_guillotina):
    access_token, _claims = issue_access_token(
        issuer="http://localhost/db/guillotina",
        subject="root",
        audience=["http://localhost/db/guillotina"],
        client_id="client",
        scope=["guillotina:access"],
    )
    assert await OAuthJWTValidator().validate({"type": token_type, "token": access_token}) is None


@pytest.mark.asyncio
async def test_oauth_html_pages_deny_framing(dummy_guillotina):
    response = oauth_error_page("Error", "Message", status=400)
    assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none'"
    assert response.headers["X-Frame-Options"] == "DENY"


@pytest.mark.asyncio
@pytest.mark.app_settings(
    {
        "applications": ["guillotina", "guillotina.contrib.oauth"],
        "oauth": {"scopes_supported": ["guillotina:access", "guillotina:extra"]},
    }
)
async def test_oauth_client_scope_registration_limits_requested_scopes(dummy_guillotina):
    client = build_client_from_registration({"redirect_uris": ["http://localhost/callback"]})
    assert client["scope"] == "guillotina:access"
    assert scopes_registered_for_client(client, ["guillotina:access"])
    assert not scopes_registered_for_client(client, ["guillotina:access", "guillotina:extra"])

    client = build_client_from_registration(
        {"redirect_uris": ["http://localhost/callback"], "scope": "guillotina:access guillotina:extra"}
    )
    assert scopes_registered_for_client(client, ["guillotina:access", "guillotina:extra"])


@pytest.mark.asyncio
@pytest.mark.app_settings(
    {
        "applications": ["guillotina", "guillotina.contrib.oauth"],
        "oauth": {"scopes_supported": ["guillotina:access", "guillotina:extra"]},
    }
)
async def test_oauth_client_registration_rejects_unusable_scope(dummy_guillotina):
    with pytest.raises(HTTPBadRequest):
        build_client_from_registration(
            {"redirect_uris": ["http://localhost/callback"], "scope": "guillotina:extra"}
        )


def test_oauth_configured_issuer_must_be_safe():
    assert (
        validate_issuer("https://api.example.com/db/guillotina/") == "https://api.example.com/db/guillotina"
    )
    assert validate_issuer("http://localhost/db/guillotina") == "http://localhost/db/guillotina"

    for issuer in (
        "api.example.com/db/guillotina",
        "http://api.example.com/db/guillotina",
        "https://api.example.com/db/guillotina?x=1",
        "https://api.example.com/db/guillotina#fragment",
        "https://user:pass@api.example.com/db/guillotina",
    ):
        with pytest.raises(RuntimeError):
            validate_issuer(issuer)


@pytest.mark.asyncio
@pytest.mark.app_settings(
    {
        "applications": ["guillotina", "guillotina.contrib.oauth"],
        "oauth": {"issuer": "https://issuer.example.com/db/guillotina/", "trust_proxy_headers": True},
    }
)
async def test_oauth_configured_issuer_overrides_request_headers(dummy_guillotina):
    request = make_mocked_request(
        "GET",
        "/db/guillotina/.well-known/oauth-authorization-server",
        headers={"Host": "evil.example", "X-Forwarded-Proto": "http"},
    )
    container = Container()
    container.__name__ = "guillotina"
    assert container_issuer_url(request, container) == "https://issuer.example.com/db/guillotina"


@pytest.mark.asyncio
@pytest.mark.app_settings({"applications": ["guillotina", "guillotina.contrib.oauth"]})
async def test_oauth_required_audience_can_be_extended(dummy_guillotina):
    def resolver(request, container):
        if request.path.endswith("/@custom-protocol"):
            return f"{container_issuer_url(request, container)}/@custom-protocol"

    register_oauth_audience_resolver(resolver)
    container = Container()
    container.__name__ = "guillotina"

    request = make_mocked_request("GET", "/db/guillotina/@custom-protocol")
    assert oauth_required_audience(request, container) == "http://localhost/guillotina/@custom-protocol"

    request = make_mocked_request("GET", "/db/guillotina/@addons")
    assert oauth_required_audience(request, container) == "http://localhost/guillotina"


class _FakeRedisDriver:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, data, *, expire=None):
        self.values[key] = data


@pytest.mark.asyncio
@pytest.mark.app_settings(
    {"applications": ["guillotina", "guillotina.contrib.oauth", "guillotina.contrib.redis"], "redis": {}}
)
async def test_oauth_rate_limit_uses_redis_when_configured(monkeypatch, dummy_guillotina):
    from guillotina.contrib.oauth.utils import ratelimit

    reset_rate_limits()
    driver = _FakeRedisDriver()

    async def _driver():
        return driver

    monkeypatch.setattr(ratelimit, "_get_redis_driver", _driver)
    assert await rate_limit_exceeded("redis-key", limit=2, window=60, now=10) is False
    assert await rate_limit_exceeded("redis-key", limit=2, window=60, now=11) is False
    assert await rate_limit_check("redis-key", limit=2, window=60, now=12) is True
    assert await rate_limit_exceeded("redis-key", limit=2, window=60, now=12) is True
    assert "oauth-rate-limit:v1:redis-key" in driver.values
    reset_rate_limits()
