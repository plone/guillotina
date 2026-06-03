import asyncio
from datetime import timezone

import pytest

from guillotina import task_vars
from guillotina.contrib.oauth.storage import utility
from guillotina.contrib.oauth.storage.access import get_oauth_store, oauth_container_db_key
from guillotina.contrib.oauth.storage.interfaces import IOAuthStore
from guillotina.contrib.oauth.storage.pg.repository import OAuthRepository, _parse_dt
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


def test_oauth_repository_parses_naive_datetimes_as_utc():
    parsed = _parse_dt("2026-01-01T00:00:00")
    assert parsed.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_ensure_oauth_tables_tracks_initialization_per_pool(monkeypatch):
    class FakeAcquire:
        def __init__(self, pool):
            self.pool = pool

        async def __aenter__(self):
            return self.pool

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakePool:
        def __init__(self):
            self.executed = []

        def acquire(self):
            return FakeAcquire(self)

        async def execute(self, ddl):
            self.executed.append(ddl)

    monkeypatch.setattr(utility, "OAUTH_DDL", ["SELECT 1"])
    monkeypatch.setattr(utility, "_ddl_locks", {})
    monkeypatch.setattr(utility, "_ddl_initialized", set())

    first_storage = type("Storage", (), {"pool": FakePool()})()
    second_storage = type("Storage", (), {"pool": FakePool()})()

    await utility.ensure_oauth_tables(first_storage)
    await utility.ensure_oauth_tables(first_storage)
    await utility.ensure_oauth_tables(second_storage)

    assert first_storage.pool.executed == ["SELECT 1"]
    assert second_storage.pool.executed == ["SELECT 1"]
