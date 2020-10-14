from .memcache import record_memory_op
from guillotina import app_settings
from guillotina.component import query_utility
from guillotina.contrib.cache import CACHE_PREFIX
from guillotina.contrib.cache import memcache
from guillotina.contrib.cache import serialize
from guillotina.contrib.cache.lru import LRU
from guillotina.exceptions import NoPubSubUtility
from guillotina.interfaces import IPubSubUtility
from guillotina.profile import profilable
from guillotina.utils import resolve_dotted_name
from sys import getsizeof
from typing import List
from typing import Optional

import asyncio
import asyncpg
import logging
import pickle
import uuid


try:
    import prometheus_client
    from prometheus_client.utils import INF

    KB = 1024
    MB = 1024 * KB

    CACHE_RECORD_SIZE = prometheus_client.Histogram(
        "guillotina_cache_record_size",
        "Record size histogram of objects in cache",
        buckets=(1 * KB, 10 * KB, 50 * KB, 100 * KB, 500 * KB, 2 * MB, 5 * MB, INF),
    )

    def record_size_metric(size: int) -> None:
        CACHE_RECORD_SIZE.observe(size)


except ImportError:

    def record_size_metric(size: int) -> None:
        ...


logger = logging.getLogger("guillotina.contrib.cache")
_default_size = 1024
_basic_types = (bytes, str, int, float)


class CacheUtility:
    _memory_cache: LRU
    _ignored_tids: List[str]
    _subscriber: Optional[IPubSubUtility]
    _uid: str

    def __init__(self, settings=None, loop=None):
        self._loop = loop
        self._settings = {}
        self._ignored_tids = []
        self._subscriber = None
        self._obj_driver = None  # driver for obj cache
        self._uid = uuid.uuid4().hex
        self.initialized = False

    @profilable
    async def initialize(self, app=None):
        self._memory_cache = memcache.get_memory_cache()
        settings = app_settings["cache"]
        if settings.get("driver"):
            klass = resolve_dotted_name(settings["driver"])
            if klass is not None:
                self._obj_driver = await klass.get_driver()
        # We need to make sure that we have also PubSub
        self._subscriber = query_utility(IPubSubUtility)
        if self._subscriber is None and settings.get("updates_channel"):
            raise NoPubSubUtility()
        elif settings.get("updates_channel") not in (None, ""):
            await self._subscriber.initialized()
            await self._subscriber.subscribe(settings["updates_channel"], self._uid, self.invalidate)
        self.initialized = True

    async def finalize(self, app=None):
        settings = app_settings["cache"]
        if self._subscriber is not None:
            try:
                await self._subscriber.unsubscribe(settings["updates_channel"], self._uid)
            except (asyncio.CancelledError, RuntimeError):
                # task cancelled, let it die
                return
        if self._obj_driver is not None:
            await self._obj_driver.finalize()
        self.initialized = False

    # Get a object from cache
    async def get(self, key):
        try:
            if key in self._memory_cache:
                logger.debug("Retrieved {} from memory cache".format(key))
                record_memory_op("get", "hit")
                return self._memory_cache[key]
            record_memory_op("get", "miss")
            if self._obj_driver is not None:
                val = await self._obj_driver.get(CACHE_PREFIX + key)
                if val is not None:
                    logger.debug("Retrieved {} from cache".format(key))
                    val = serialize.loads(val)
                    size = self.get_size(val)
                    self._memory_cache.set(key, val, size)
                    return val
        except Exception:
            logger.warning("Error getting cache value", exc_info=True)

    def get_size(self, value):
        if isinstance(value, (dict, asyncpg.Record)):
            if "state" in value:
                return len(value["state"])
        if isinstance(value, list) and len(value) > 0:
            # if its a list, guesss from first gey the length, and
            # estimate it from the total lenghts on the list..
            return getsizeof(value[0]) * len(value)
        if isinstance(value, _basic_types):
            return getsizeof(value)
        return _default_size

    # Set a object from cache
    async def set(self, keys, value, ttl=None):
        if not isinstance(keys, list):
            keys = [keys]
        in_memory_size = size = self.get_size(value)
        for key in keys:
            record_size_metric(size)
            try:
                self._memory_cache.set(key, value, in_memory_size)
                record_memory_op("set", "none")
                if ttl is None:
                    ttl = self._settings.get("ttl", 3600)
                if self._obj_driver is not None:
                    stored_value = serialize.dumps(value)
                    await self._obj_driver.set(CACHE_PREFIX + key, stored_value, expire=ttl)
                logger.debug("set {} in cache".format(key))
            except Exception:
                logger.warning("Error setting cache value", exc_info=True)
            in_memory_size = 0  # additional keys to set have 0 size in in-memory cache

    @profilable
    # Delete a set of objects from cache
    async def delete_all(self, keys):
        delete_keys = []
        for key in keys:
            delete_keys.append(CACHE_PREFIX + key)
            if key in self._memory_cache:
                del self._memory_cache[key]
                record_memory_op("delete", "none")
        if len(delete_keys) > 0 and self._obj_driver is not None:
            await self._obj_driver.delete_all(delete_keys)

    # Delete a set of objects from cache
    async def delete(self, key):
        try:
            if key in self._memory_cache:
                del self._memory_cache[key]
                record_memory_op("delete", "hit")
            else:
                record_memory_op("delete", "miss")
            if self._obj_driver is not None:
                await self._obj_driver.delete(key)
        except Exception:
            logger.warning("Error removing from cache", exc_info=True)

    # Clean all cache
    async def clear(self):
        try:
            self._memory_cache.clear()
            if self._obj_driver is not None:
                await self._obj_driver.flushall()
            logger.debug("Cleared cache")
        except Exception:
            logger.warning("Error clearing cache", exc_info=True)

    @profilable
    # Called by the subscription to invalidations
    async def invalidate(self, *, data=None, sender=None):
        if isinstance(data, (bytes, str)):
            try:
                data = serialize.loads(data)
            except (TypeError, pickle.UnpicklingError):
                logger.warning("Invalid message")
                return

        assert isinstance(data, dict)
        assert "tid" in data
        assert "keys" in data
        if data["tid"] in self._ignored_tids:
            # on the same thread, ignore this sucker...
            self._ignored_tids.remove(data["tid"])
            return

        for key in data["keys"]:
            if key in self._memory_cache:
                del self._memory_cache[key]

        push = data.get("push", {})
        if isinstance(push, dict):
            for cache_key, ob in push.items():
                self._memory_cache.set(cache_key, ob, self.get_size(ob))

        # clean up possible memory leak
        while len(self._ignored_tids) > 100:
            self._ignored_tids.pop(0)

    def ignore_tid(self, tid):
        # so we don't invalidate twice...
        self._ignored_tids.append(tid)

    async def send_invalidation(self, keys_to_publish, push=None):
        if self._subscriber:
            await self._subscriber.publish(
                app_settings["cache"]["updates_channel"],
                self._uid,
                {"keys": keys_to_publish, "push": push or {}},
            )

    async def get_stats(self):
        result = {"in-memory": {"size": len(self._memory_cache), "stats": self._memory_cache.get_stats()}}
        if self._obj_driver is not None:
            result["network"] = await self._obj_driver.info()
        return result
