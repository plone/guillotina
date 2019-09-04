from guillotina.component import get_utility
from guillotina.contrib.cache.strategy import BasicCache
from guillotina.db.transaction import Transaction
from guillotina.interfaces import ICacheUtility
from guillotina.tests import mocks
from guillotina.tests.utils import create_content

import pytest


DEFAULT_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.cache"],
    "cache": {"updates_channel": None, "driver": None},
}


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_cache_set(guillotina_main, loop):
    util = get_utility(ICacheUtility)
    assert util.initialized
    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set("bar", oid="foo")
    # but also in memory
    assert util._memory_cache.get("root-foo") == "bar"
    # and api matches..
    assert await rcache.get(oid="foo") == "bar"


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_cache_delete(guillotina_main, loop):
    util = get_utility(ICacheUtility)
    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set("bar", oid="foo")
    # make sure it is in redis
    assert util._memory_cache.get("root-foo") == "bar"
    assert await rcache.get(oid="foo") == "bar"

    # now delete
    await rcache.delete("root-foo")
    assert await rcache.get(oid="foo") is None


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_cache_clear(guillotina_main, loop):
    util = get_utility(ICacheUtility)
    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set("bar", oid="foo")
    assert util._memory_cache.get("root-foo") == "bar"
    assert await rcache.get(oid="foo") == "bar"

    await rcache.clear()
    assert await rcache.get(oid="foo") is None


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_invalidate_object(guillotina_main, loop):
    util = get_utility(ICacheUtility)
    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    content = create_content()
    trns.modified = {content.__uuid__: content}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set("foobar", oid=content.__uuid__)
    assert util._memory_cache.get("root-" + content.__uuid__) == "foobar"
    assert await rcache.get(oid=content.__uuid__) == "foobar"

    await rcache.close(invalidate=True)
    assert await rcache.get(oid=content.__uuid__) is None


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_cache_object(guillotina_main, loop):
    tm = mocks.MockTransactionManager()
    storage = tm._storage
    txn = Transaction(tm)
    cache = BasicCache(txn)
    txn._cache = cache
    ob = create_content()
    storage.store(None, None, None, ob, txn)
    loaded = await txn.get(ob.__uuid__)
    assert id(loaded) != id(ob)
    assert loaded.__uuid__ == ob.__uuid__
    assert cache._hits == 0
    assert cache._misses == 1

    # and load from cache
    await txn.get(ob.__uuid__)
    assert cache._hits == 1


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_cache_object_from_child(guillotina_main, loop):
    tm = mocks.MockTransactionManager()
    storage = tm._storage
    txn = Transaction(tm)
    cache = BasicCache(txn)
    txn._cache = cache
    ob = create_content()
    parent = create_content()
    ob.__parent__ = parent
    storage.store(None, None, None, parent, txn)
    storage.store(None, None, None, ob, txn)

    loaded = await txn.get_child(parent, ob.id)
    assert cache._hits == 0
    loaded = await txn.get_child(parent, ob.id)
    assert cache._hits == 1

    assert id(loaded) != id(ob)
    assert loaded.__uuid__ == ob.__uuid__


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_do_not_cache_large_object(guillotina_main, loop):
    tm = mocks.MockTransactionManager()
    storage = tm._storage
    txn = Transaction(tm)
    cache = BasicCache(txn)
    txn._cache = cache
    ob = create_content()
    ob.foobar = "X" * cache.max_cache_record_size  # push size above cache threshold
    storage.store(None, None, None, ob, txn)
    loaded = await txn.get(ob.__uuid__)
    assert id(loaded) != id(ob)
    assert loaded.__uuid__ == ob.__uuid__
