from guillotina import app_settings
from guillotina.component import get_utility
from guillotina.contrib.cache import CACHE_PREFIX
from guillotina.contrib.cache import serialize
from guillotina.contrib.cache.strategy import BasicCache
from guillotina.interfaces import ICacheUtility
from guillotina.tests import mocks
from guillotina.tests.utils import create_content
from guillotina.utils import resolve_dotted_name

import asyncio
import pickle
import pytest


DEFAULT_SETTINGS = {
    "applications": [
        "guillotina",
        "guillotina.contrib.redis",
        "guillotina.contrib.cache",
        "guillotina.contrib.pubsub",
    ],
    "cache": {"updates_channel": "guillotina", "driver": "guillotina.contrib.redis"},
}


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_invalidate_object(redis_container, guillotina_main, loop):
    util = get_utility(ICacheUtility)
    await util.initialize()
    assert util.initialized
    assert util._obj_driver is not None
    assert util._subscriber is not None

    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    content = create_content()
    trns.modified = {content.__uuid__: content}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set("foobar", oid=content.__uuid__)

    driver = await resolve_dotted_name("guillotina.contrib.redis").get_driver()
    assert serialize.loads(await driver.get(CACHE_PREFIX + "root-" + content.__uuid__)) == "foobar"
    assert util._memory_cache.get("root-" + content.__uuid__) == "foobar"
    assert await rcache.get(oid=content.__uuid__) == "foobar"

    await rcache.close(invalidate=True)
    assert await rcache.get(oid=content.__uuid__) is None


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_subscriber_invalidates(redis_container, guillotina_main, loop):
    util = get_utility(ICacheUtility)
    await util.initialize()
    assert util.initialized
    assert util._obj_driver is not None
    assert util._subscriber is not None

    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    content = create_content()
    trns.modified = {content.__uuid__: content}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set("foobar", oid=content.__uuid__)
    driver = await resolve_dotted_name("guillotina.contrib.redis").get_driver()

    assert serialize.loads(await driver.get(CACHE_PREFIX + "root-" + content.__uuid__)) == "foobar"
    assert util._memory_cache.get("root-" + content.__uuid__) == "foobar"
    assert await rcache.get(oid=content.__uuid__) == "foobar"

    assert "root-" + content.__uuid__ in util._memory_cache

    await driver.publish(
        app_settings["cache"]["updates_channel"],
        pickle.dumps(
            {"data": serialize.dumps({"tid": 32423, "keys": ["root-" + content.__uuid__]}), "ruid": "nonce"}
        ),
    )
    await asyncio.sleep(1)  # should be enough for pub/sub to finish
    assert "root-" + content.__uuid__ not in util._memory_cache


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_subscriber_ignores_trsn_on_invalidate(redis_container, guillotina_main, loop):

    util = get_utility(ICacheUtility)
    await util.initialize()
    assert util.initialized
    assert util._obj_driver is not None
    assert util._subscriber is not None

    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    content = create_content()
    trns.modified = {content.__uuid__: content}
    rcache = BasicCache(trns)
    await rcache.clear()
    driver = await resolve_dotted_name("guillotina.contrib.redis").get_driver()

    await rcache.set("foobar", oid=content.__uuid__)
    assert serialize.loads(await driver.get(CACHE_PREFIX + "root-" + content.__uuid__)) == "foobar"
    assert util._memory_cache.get("root-" + content.__uuid__) == "foobar"
    assert await rcache.get(oid=content.__uuid__) == "foobar"

    assert "root-" + content.__uuid__ in util._memory_cache

    util.ignore_tid(5555)

    await driver.publish(
        app_settings["cache"]["updates_channel"],
        pickle.dumps(
            {"data": serialize.dumps({"tid": 5555, "keys": ["root-" + content.__uuid__]}), "ruid": "nonce"}
        ),
    )
    await asyncio.sleep(1)  # should be enough for pub/sub to finish
    # should still be there because we set to ignore this tid
    assert "root-" + content.__uuid__ in util._memory_cache
    # tid should also now be removed from ignored list
    assert 5555 not in util._ignored_tids
