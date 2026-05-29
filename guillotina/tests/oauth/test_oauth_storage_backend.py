import asyncio

import pytest

from guillotina import task_vars
from guillotina.contrib.oauth.storage.access import get_oauth_store, oauth_container_db_key
from guillotina.contrib.oauth.storage.interfaces import IOAuthStore
from guillotina.contrib.oauth.storage.pg.repository import OAuthRepository
from guillotina.contrib.oauth.storage.pg.schema import OAUTH_DDL


def assert_oauth_store(store):
    assert IOAuthStore.providedBy(store)
    for name in IOAuthStore.names():
        assert asyncio.iscoroutinefunction(getattr(store, name)), name


def test_oauth_repository_implements_interface():
    store = OAuthRepository("db/guillotina")
    assert_oauth_store(store)


def test_oauth_container_db_key_includes_database_id():
    db = type("DB", (), {"id": "db"})()
    container = type("Container", (), {"id": "guillotina"})()
    token = task_vars.db.set(db)
    try:
        assert oauth_container_db_key(container) == "db/guillotina"
    finally:
        task_vars.db.reset(token)


def test_oauth_schema_uses_container_db_key():
    ddl = "\n".join(OAUTH_DDL)
    assert "container_db_key text NOT NULL" in ddl
    assert "container_id text NOT NULL" not in ddl


def test_get_oauth_store_without_pg_raises():
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        get_oauth_store(type("Container", (), {"id": "guillotina"})(), require_installed=False)
