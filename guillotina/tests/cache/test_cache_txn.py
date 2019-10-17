from guillotina import app_settings
from guillotina.annotations import AnnotationData
from guillotina.api.container import create_container
from guillotina.component import get_utility
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import ICacheUtility
from guillotina.transactions import transaction
from guillotina.utils import get_database

import pytest


DEFAULT_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.redis", "guillotina.contrib.cache"],
    "cache": {"updates_channel": None, "driver": "guillotina.contrib.redis"},
}


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_txn_uses_cached_hits_on_annotations(redis_container, guillotina_main, loop):
    util = get_utility(ICacheUtility)
    await util.initialize()

    async with transaction(db=await get_database("db")) as txn:
        root = await txn.manager.get_root()
        container = await create_container(root, "container")

        with pytest.raises(KeyError):
            # should set in cache as empty though
            await txn.get_annotation(container, "foobar")
        # should be registered as cache miss
        assert txn._cache._hits == 0
        assert txn._cache._misses == 2

        with pytest.raises(KeyError):
            # do again, should be hit this time
            await txn.get_annotation(container, "foobar")

        assert txn._cache._hits == 1
        assert txn._cache._misses == 2

        # now set a value for it and we'll retrieve it again
        annotations_container = IAnnotations(container)
        adata = AnnotationData()
        await annotations_container.async_set("foobar", adata)

    async with transaction(db=await get_database("db")) as txn:
        # everything here should be hits!
        root = await txn.manager.get_root()
        container = await root.async_get("container")

        adata = await txn.get_annotation(container, "foobar")
        # should be registered as cache miss
        assert txn._cache._hits == 2
        assert txn._cache._misses == 0

    async with transaction(db=await get_database("db")) as txn:
        # now, edit the value
        root = await txn.manager.get_root()
        container = await root.async_get("container")

        adata = await txn.get_annotation(container, "foobar")
        adata["foo"] = "bar"
        adata.register()
        # should be registered as cache miss
        assert txn._cache._hits == 2
        assert txn._cache._misses == 0

    async with transaction(db=await get_database("db")) as txn:
        # everything here should be hits!
        root = await txn.manager.get_root()
        container = await root.async_get("container")

        adata = await txn.get_annotation(container, "foobar")
        assert adata["foo"] == "bar"
        # should be registered as cache miss
        assert txn._cache._hits == 2
        assert txn._cache._misses == 0

    # same again, but clear cache implementation
    await util.clear()

    async with transaction(db=await get_database("db")) as txn:
        # everything here should be hits!
        root = await txn.manager.get_root()
        container = await root.async_get("container")

        adata = await txn.get_annotation(container, "foobar")
        assert adata["foo"] == "bar"
        # should be registered as cache miss
        assert txn._cache._hits == 0
        assert txn._cache._misses == 2


class MockSubscriber:
    def __init__(self):
        self.data = []

    async def publish(self, channel, tid, info):
        self.data.append(info)

    async def unsubscribe(self, channel, uid):
        pass


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_txn_push_updates_to_subscriber(redis_container, guillotina_main, loop):
    util = get_utility(ICacheUtility)
    await util.initialize()
    app_settings["cache"]["updates_channel"] = "foobar"
    util._subscriber = MockSubscriber()

    async with transaction(db=await get_database("db")) as txn:
        root = await txn.manager.get_root()
        await create_container(root, "container")

    assert len(util._subscriber.data) == 1
    assert "db-00000000000000000000000000000000-keys" in util._subscriber.data[0]["keys"]
    assert "db-00000000000000000000000000000000/container" in util._subscriber.data[0]["push"]


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_txn_set_value_with_no_parent(redis_container, guillotina_main, loop):
    util = get_utility(ICacheUtility)
    await util.initialize()
    app_settings["cache"]["updates_channel"] = "foobar"
    util._subscriber = MockSubscriber()

    async with transaction(db=await get_database("db")) as txn:
        root = await txn.manager.get_root()
        # root object will not have parent
        root.foo = "bar"
        root.register()

    assert len(util._subscriber.data) == 1
