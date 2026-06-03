import pytest

from guillotina.contrib.oauth.flow.clients import consent_key
from guillotina.tests.oauth.conftest import (
    OAUTH_SETTINGS,
    authorize_code,
    register_client,
    requires_pg,
    token_from_code,
    verifier_pair,
)


pytestmark = [pytest.mark.asyncio, requires_pg]


async def _authorize_get(requester, client, *, verifier=None):
    """Issue a bare GET /authorize and return the raw (value, status, headers)."""
    verifier = verifier or "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    _verifier, challenge = verifier_pair(verifier)
    params = {
        "response_type": "code",
        "client_id": client["client_id"],
        "redirect_uri": client["redirect_uris"][0],
        "scope": "guillotina:access",
        "state": "abc",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return await requester.make_request(
        "GET",
        "/db/guillotina/oauth/authorize",
        params=params,
        allow_redirects=False,
    )


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_revoke_token_deletes_consent(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client)
        token = await token_from_code(requester, client, code, verifier)

        # Consent is remembered: a fresh authorize redirects silently (302).
        _value, status, _headers = await _authorize_get(requester, client)
        assert status == 302

        # Revoking the refresh token must also drop the remembered consent.
        _resp, status = await requester(
            "POST",
            "/db/guillotina/oauth/revoke",
            data=f"client_id={client['client_id']}&token={token['refresh_token']}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 200

        # The grant can no longer be silently re-issued: consent is required again.
        _value, status, _headers = await _authorize_get(requester, client)
        assert status == 200


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_list_and_revoke_consents_endpoint(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client)
        await token_from_code(requester, client, code, verifier)

        listing, status = await requester("GET", "/db/guillotina/oauth/consents")
        assert status == 200
        # The shared test database may carry consents from other tests, so scope
        # the assertions to the client registered here.
        ours = [c for c in listing["consents"] if c["client_id"] == client["client_id"]]
        assert len(ours) == 1
        entry = ours[0]
        assert entry["client_name"] == client["client_name"]
        assert entry["scope"] == ["guillotina:access"]
        ckey = entry["consent_key"]

        revoked, status = await requester(
            "POST",
            "/db/guillotina/oauth/consents",
            data=f"consent_key={ckey}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 200

        listing, status = await requester("GET", "/db/guillotina/oauth/consents")
        assert status == 200
        ours = [c for c in listing["consents"] if c["client_id"] == client["client_id"]]
        assert ours == []

        # Revoking consent forces the consent screen on the next authorize.
        _value, status, _headers = await _authorize_get(requester, client)
        assert status == 200


@pytest.mark.app_settings(OAUTH_SETTINGS)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_revoke_unknown_consent_returns_404(container_install_requester):
    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client)
        await token_from_code(requester, client, code, verifier)

        _resp, status = await requester(
            "POST",
            "/db/guillotina/oauth/consents",
            data="consent_key=does-not-exist",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert status == 404


@pytest.mark.app_settings(
    {
        "applications": ["guillotina", "guillotina.contrib.oauth"],
        "oauth": {"consent_ttl": -1},
    }
)
async def test_consent_ttl_expires(guillotina_main):
    from guillotina.component import get_utility
    from guillotina.contrib.oauth.storage.pg.repository import OAuthRepository
    from guillotina.contrib.oauth.storage.utility import ensure_oauth_tables
    from guillotina.interfaces import IApplication
    from guillotina.transactions import transaction

    root = get_utility(IApplication, name="root")
    await ensure_oauth_tables(root["db"].storage)

    async with transaction(db=root["db"]):
        store = OAuthRepository("db/consent-ttl")
        scopes = ["guillotina:access"]
        resources = ["http://localhost/db/guillotina"]
        ckey = consent_key("root", "ttl-client", scopes, resources)
        await store.create_consent(
            ckey,
            user_id="root",
            client_id="ttl-client",
            scope=scopes,
            resource=resources,
        )
        # A negative TTL produces an already-expired consent.
        assert await store.has_consent(ckey) is False
        assert await store.list_consents("root") == []
        await store.delete_container_data()


@pytest.mark.app_settings(
    {
        "applications": ["guillotina", "guillotina.contrib.oauth"],
        "oauth": {"consent_ttl": 0},
    }
)
async def test_consent_ttl_zero_never_expires(guillotina_main):
    from guillotina.component import get_utility
    from guillotina.contrib.oauth.storage.pg.repository import OAuthRepository
    from guillotina.contrib.oauth.storage.utility import ensure_oauth_tables
    from guillotina.interfaces import IApplication
    from guillotina.transactions import transaction

    root = get_utility(IApplication, name="root")
    await ensure_oauth_tables(root["db"].storage)

    async with transaction(db=root["db"]):
        store = OAuthRepository("db/consent-ttl-zero")
        scopes = ["guillotina:access"]
        resources = ["http://localhost/db/guillotina"]
        ckey = consent_key("root", "zero-client", scopes, resources)
        await store.create_consent(
            ckey,
            user_id="root",
            client_id="zero-client",
            scope=scopes,
            resource=resources,
        )
        assert await store.has_consent(ckey) is True
        records = await store.list_consents("root")
        assert len(records) == 1
        assert records[0]["expires_at"] is None
        assert await store.delete_consent(ckey, user_id="root") is True
        assert await store.has_consent(ckey) is False
        await store.delete_container_data()
