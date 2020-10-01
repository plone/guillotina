from guillotina.component import get_utility
from guillotina.contrib.cache import CACHE_PREFIX
from guillotina.contrib.cache import serialize
from guillotina.contrib.cache.strategy import BasicCache
from guillotina.interfaces import ICacheUtility
from guillotina.tests import mocks
from guillotina.utils import resolve_dotted_name

import pytest


DEFAULT_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.redis", "guillotina.contrib.cache"],
    "cache": {"updates_channel": None, "driver": "guillotina.contrib.redis"},
}


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_cache_set(redis_container, guillotina_main, loop):
    util = get_utility(ICacheUtility)
    await util.initialize()
    assert util.initialized
    assert util._obj_driver is not None
    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set("bar", oid="foo")
    # make sure it is in redis
    driver = await resolve_dotted_name("guillotina.contrib.redis").get_driver()

    val = await driver.get(CACHE_PREFIX + "root-foo")
    assert serialize.loads(val) == "bar"
    # but also in memory
    assert util._memory_cache.get("root-foo") == "bar"
    # and api matches..
    assert await rcache.get(oid="foo") == "bar"
    await util.finalize(None)


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_cache_delete(redis_container, guillotina_main, loop):
    util = get_utility(ICacheUtility)
    await util.initialize()
    assert util.initialized
    assert util._obj_driver is not None

    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set("bar", oid="foo")
    # make sure it is in redis
    driver = await resolve_dotted_name("guillotina.contrib.redis").get_driver()

    assert serialize.loads(await driver.get(CACHE_PREFIX + "root-foo")) == "bar"
    assert util._memory_cache.get("root-foo") == "bar"
    assert await rcache.get(oid="foo") == "bar"

    # now delete
    await rcache.delete("root-foo")
    assert await rcache.get(oid="foo") is None
    await util.finalize(None)


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_cache_clear(redis_container, guillotina_main, loop):
    util = get_utility(ICacheUtility)
    await util.initialize()

    assert util.initialized
    assert util._obj_driver is not None

    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set("bar", oid="foo")
    # make sure it is in redis
    driver = await resolve_dotted_name("guillotina.contrib.redis").get_driver()

    assert serialize.loads(await driver.get(CACHE_PREFIX + "root-foo")) == "bar"
    assert util._memory_cache.get("root-foo") == "bar"
    assert await rcache.get(oid="foo") == "bar"

    await rcache.clear()
    assert await rcache.get(oid="foo") is None
    await util.finalize(None)


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_set_multiple_cache_keys_size(redis_container, guillotina_main, loop):
    util = get_utility(ICacheUtility)
    await util.initialize()
    assert util.initialized
    assert util._obj_driver is not None
    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set({"state": "foobar"}, keyset=[{"oid": "foo"}, {"container": "foobar", "id": "foobar"}])
    assert util._memory_cache.get_memory() == 6
    await util.finalize(None)


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_get_stats(redis_container, guillotina_main, loop):
    util = get_utility(ICacheUtility)
    await util.initialize()
    assert util.initialized
    assert util._obj_driver is not None
    stats = await util.get_stats()
    assert len(stats["in-memory"])
    assert len(stats["network"])
