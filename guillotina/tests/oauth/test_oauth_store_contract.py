import pytest

from guillotina.contrib.oauth.flow.clients import consent_key
from guillotina.contrib.oauth.flow.tokens import opaque_token
from guillotina.tests.oauth.conftest import requires_pg
from guillotina.tests.oauth.test_oauth_storage_backend import assert_oauth_store
from guillotina.transactions import transaction


pytestmark = [pytest.mark.asyncio, requires_pg]


async def run_oauth_store_contract(store):
    assert_oauth_store(store)

    client = {
        "client_id": "contract-client",
        "client_name": "Contract Test",
        "redirect_uris": ["http://127.0.0.1:12345/callback"],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "scope": "guillotina:access",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    await store.create_client(client)
    loaded = await store.get_client("contract-client")
    assert loaded["client_name"] == "Contract Test"

    scopes = ["guillotina:access"]
    resources = ["http://localhost/db/guillotina"]
    ckey = consent_key("root", client["client_id"], scopes, resources)
    assert await store.has_consent(ckey) is False
    await store.create_consent(
        ckey,
        user_id="root",
        client_id=client["client_id"],
        scope=scopes,
        resource=resources,
    )
    assert await store.has_consent(ckey) is True

    raw_code = opaque_token("goc_")
    code_record = await store.create_code(
        raw_code=raw_code,
        client_id=client["client_id"],
        user_id="root",
        redirect_uri=client["redirect_uris"][0],
        scope=scopes,
        resource=resources,
        code_challenge="challenge",
    )
    assert await store.get_active_code(raw_code) is not None

    standalone_refresh = opaque_token("gor_")
    await store.create_refresh_token(
        raw_token=standalone_refresh,
        client_id=client["client_id"],
        user_id="root",
        scope=scopes,
        resource=resources,
    )
    assert await store.get_valid_refresh(standalone_refresh) is not None
    await store.revoke_refresh_token(standalone_refresh)
    assert await store.get_valid_refresh(standalone_refresh) is None
    assert (await store.get_refresh_token(standalone_refresh))["revoked_at"] is not None

    linked_refresh = opaque_token("gor_")
    await store.create_refresh_token(
        raw_token=linked_refresh,
        client_id=client["client_id"],
        user_id="root",
        scope=scopes,
        resource=resources,
        auth_code_hash=code_record["code_hash"],
    )
    await store.delete_code(code_record["code_hash"])
    assert await store.get_active_code(raw_code) is None
    assert await store.revoke_refresh_tokens_by_auth_code(code_record["code_hash"]) is True
    assert await store.get_valid_refresh(linked_refresh) is None
    assert (await store.get_refresh_token(linked_refresh))["revoked_at"] is not None

    await store.delete_container_data()
    assert await store.get_client("contract-client") is None
    assert await store.has_consent(ckey) is False


@pytest.mark.app_settings(
    {
        "applications": ["guillotina", "guillotina.contrib.oauth"],
    }
)
async def test_postgresql_oauth_store_contract(guillotina_main):
    from guillotina.component import get_utility
    from guillotina.contrib.oauth.storage.pg.repository import OAuthRepository
    from guillotina.contrib.oauth.storage.utility import ensure_oauth_tables
    from guillotina.interfaces import IApplication

    root = get_utility(IApplication, name="root")
    await ensure_oauth_tables(root["db"].storage)

    async with transaction(db=root["db"]):
        store = OAuthRepository("db/pg-contract")
        await run_oauth_store_contract(store)


@pytest.mark.app_settings(
    {
        "applications": ["guillotina", "guillotina.contrib.oauth"],
        "auth_extractors": [
            "guillotina.auth.extractors.BearerAuthPolicy",
            "guillotina.auth.extractors.BasicAuthPolicy",
            "guillotina.auth.extractors.WSTokenAuthPolicy",
            "guillotina.auth.extractors.CookiePolicy",
        ],
    }
)
@pytest.mark.parametrize("install_addons", [["oauth"]])
async def test_oauth_flow_with_postgresql_store(container_install_requester):
    from guillotina.component import get_utility
    from guillotina.contrib.oauth.storage.utility import ensure_oauth_tables
    from guillotina.interfaces import IApplication
    from guillotina.tests.oauth.conftest import authorize_code, register_client, token_from_code

    root = get_utility(IApplication, name="root")
    await ensure_oauth_tables(root["db"].storage)

    async with container_install_requester as requester:
        client = await register_client(requester)
        code, verifier = await authorize_code(requester, client)
        token = await token_from_code(requester, client, code, verifier)
        assert token["access_token"]
