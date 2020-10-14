from guillotina import app_settings
from guillotina import configure
from guillotina.component import query_utility
from guillotina.db.cache.base import BaseCache
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionCache
from guillotina.exceptions import NoChannelConfigured
from guillotina.exceptions import NoPubSubUtility
from guillotina.interfaces import ICacheUtility
from guillotina.profile import profilable
from typing import Any
from typing import Dict
from typing import List

import asyncio
import logging


logger = logging.getLogger("guillotina")

_default_size = 1024
_basic_types = (bytes, str, int, float)


@configure.adapter(for_=ITransaction, provides=ITransactionCache, name="basic")
class BasicCache(BaseCache):
    max_publish_objects = 20

    def __init__(self, transaction):
        super().__init__(transaction)
        self._utility = query_utility(ICacheUtility)
        if self._utility is None:
            logger.info("No cache utility configured")
        self._keys_to_publish = []
        self._stored_objects = []

    @property
    def push_enabled(self):
        return app_settings["cache"].get("push", True)

    @profilable
    async def get(self, **kwargs):
        if self._utility is None:
            return None
        key = self.get_key(**kwargs)
        obj = await self._utility.get(key)
        if obj is not None:
            self._hits += 1
        else:
            self._misses += 1
        return obj

    @profilable
    async def set(self, value, keyset: List[Dict[str, Any]] = None, **kwargs):
        if self._utility is None:
            return
        if keyset is None:
            keyset = [kwargs]
        await self._utility.set([self.get_key(**opts) for opts in keyset], value)
        self._stored += 1

    @profilable
    async def clear(self):
        if self._utility is None:
            return
        await self._utility.clear()

    @profilable
    async def delete(self, key):
        if self._utility is None:
            return
        await self._utility.delete_all([key])

    @profilable
    async def delete_all(self, keys):
        if self._utility is None:
            return
        self._keys_to_publish.extend(keys)
        await self._utility.delete_all(keys)

    async def store_object(self, obj, pickled):
        if len(self._stored_objects) < self.max_publish_objects:
            self._stored_objects.append((obj, pickled))
            # also assume these objects are then stored
            # (even though it's done after the request)
            self._stored += 1

    @profilable
    async def _extract_invalidation_keys(self, groups):
        invalidated = []
        for data, type_ in groups:
            for oid, ob in data.items():
                invalidated.extend(self.get_cache_keys(ob, type_))
        return invalidated

    @profilable
    async def close(self, invalidate=True, publish=True):
        """
        - invalidate:
            - invalidate object caches for the objects involved in the txn
            - use False when you do not want changes in the transaction to invalidate the cache
        - publish:
            - synchronize changes to objects with caches
            - use False when you do not want changes to synchronize

        For example, on conflict error:
            - invalidate=True -- we want objects involved in the txn to be invalidated so they are loaded from db
            - publish=False -- objects involved in the txn should not be pushed to caches
        """
        if self._utility is None:
            return
        try:
            if invalidate:
                # A commit worked so we want to invalidate
                keys_to_invalidate = await self._extract_invalidation_keys(
                    [
                        (self._transaction.modified, "modified"),
                        (self._transaction.added, "added"),
                        (self._transaction.deleted, "deleted"),
                    ]
                )
                await self.delete_all(keys_to_invalidate)

                if publish:
                    await self.fill_cache()
                    if len(self._keys_to_publish) > 0 and self._utility._subscriber is not None:
                        keys = self._keys_to_publish
                        asyncio.ensure_future(self.synchronize(keys))
                    else:
                        self._stored_objects.clear()
            else:
                self._stored_objects.clear()

            self._keys_to_publish = []
        except Exception:  # pragma: no cover
            self._stored_objects.clear()
            self._keys_to_publish = []
            logger.warning("Error closing connection", exc_info=True)

    async def fill_cache(self):
        for obj, pickled in self._stored_objects:
            val = {"state": pickled, "zoid": obj.__uuid__, "tid": obj.__serial__, "id": obj.__name__}
            if obj.__of__:
                await self.set(
                    val, [dict(oid=obj.__of__, id=obj.__name__, variant="annotation"), dict(oid=obj.__uuid__)]
                )
            else:
                keyset = [dict(oid=obj.__uuid__)]
                if obj.__parent__:
                    val["parent_id"] = obj.__parent__.__uuid__
                    keyset.append(dict(container=obj.__parent__, id=obj.__name__))
                else:
                    # root object does not have a parent
                    val["parent_id"] = None
                await self.set(val, keyset)

    @profilable
    async def synchronize(self, keys_to_publish):
        """
        publish cache changes on redis
        """
        if self._utility._subscriber is None:  # pragma: no cover
            raise NoPubSubUtility()
        if app_settings.get("cache", {}).get("updates_channel", None) is None:  # pragma: no cover
            raise NoChannelConfigured()
        push = {}
        if self.push_enabled:
            for obj, pickled in self._stored_objects:
                val = {"state": pickled, "zoid": obj.__uuid__, "tid": obj.__serial__, "id": obj.__name__}
                if obj.__of__:
                    ob_key = self.get_key(oid=obj.__of__, id=obj.__name__, variant="annotation")
                else:
                    if obj.__parent__:
                        ob_key = self.get_key(container=obj.__parent__, id=obj.__name__)
                    else:
                        ob_key = self.get_key(oid=obj.__uuid__)
                push[ob_key] = val

        self._stored_objects.clear()
        self._utility.ignore_tid(self._transaction._tid)
        await self._utility._subscriber.publish(
            app_settings["cache"]["updates_channel"],
            self._transaction._tid,
            {"tid": self._transaction._tid, "keys": keys_to_publish, "push": push},
        )
