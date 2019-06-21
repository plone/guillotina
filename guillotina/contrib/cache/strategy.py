import asyncio
import logging

from guillotina import app_settings
from guillotina import configure
from guillotina.component import query_utility
from guillotina.contrib.cache import serialize
from guillotina.db.cache.base import BaseCache
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionCache
from guillotina.exceptions import NoPubSubUtility
from guillotina.interfaces import ICacheUtility
from guillotina.interfaces import IPubSubUtility
from guillotina.profile import profilable


logger = logging.getLogger('guillotina_rediscache')

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
    async def set(self, value, **kwargs):
        if self._utility is None:
            return
        key = self.get_key(**kwargs)
        await self._utility.set(key, value)
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
        for key in keys:
            self._keys_to_publish.append(key)
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
    async def close(self, invalidate=True):
        if self._utility is None:
            return
        try:

            if invalidate:
                # A commit worked so we want to invalidate
                keys_to_invalidate = await self._extract_invalidation_keys([
                    (self._transaction.modified, 'modified'),
                    (self._transaction.added, 'added'),
                    (self._transaction.deleted, 'deleted')
                ])
                await self.delete_all(keys_to_invalidate)

            if len(self._keys_to_publish) > 0:
                asyncio.ensure_future(self.synchronize())
            self._keys_to_publish = []
            self._stored_objects = []
        except Exception:
            logger.warning('Error closing connection', exc_info=True)

    @profilable
    async def synchronize(self):
        '''
        publish cache changes on redis
        '''
        push = {}
        for obj, pickled in self._stored_objects:
            val = {
                'state': pickled,
                'zoid': obj.__uuid__,
                'tid': obj.__serial__,
                'id': obj.__name__
            }
            if obj.__of__:
                ob_key = self.get_key(
                    oid=obj.__of__, id=obj.__name__, variant='annotation')
                await self.set(
                    val, oid=obj.__of__, id=obj.__name__, variant='annotation')
            else:
                ob_key = self.get_key(
                    container=obj.__parent__, id=obj.__name__)
                await self.set(
                    val, container=obj.__parent__, id=obj.__name__)

            if ob_key in self._keys_to_publish:
                self._keys_to_publish.remove(ob_key)
            push[ob_key] = val

        channel_utility = query_utility(IPubSubUtility)
        if channel_utility is None:
            raise NoPubSubUtility()
        await channel_utility.publish(
            app_settings['cache']['updates_channel'],
            serialize.dumps({
                'tid': self._transaction._tid,
                'keys': self._keys_to_publish,
                'push': push
            }))
