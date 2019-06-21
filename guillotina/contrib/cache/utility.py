from guillotina import app_settings
from guillotina.component import query_utility
from guillotina.interfaces import IPubSubUtility
from guillotina.contrib.cache import CACHE_PREFIX
from guillotina.contrib.cache import serialize
from guillotina.contrib.cache import memcache
from guillotina.exceptions import NoPubSubUtility
from guillotina.profile import profilable
from guillotina.utils import resolve_dotted_name
from sys import getsizeof

import asyncio
import logging
import pickle
import uuid


logger = logging.getLogger('guillotina.contrib.cache')
_default_size = 1024
_basic_types = (bytes, str, int, float)


class CacheUtility:

    def __init__(self, settings=None, loop=None):
        self._loop = loop
        self._settings = {}
        self._ignored_tids = []
        self._subscriber = None
        self._memory_cache = None
        self._obj_driver = None  # driver for obj cache
        self._uid = uuid.uuid4().hex
        self.initialized = False

    @profilable
    async def initialize(self, app=None):
        self._memory_cache = memcache.get_memory_cache()
        settings = app_settings['cache']
        if settings['driver'] != '':
            klass = resolve_dotted_name(settings['driver'])
            if klass is not None:
                self._obj_driver = await klass.get_driver()
        # We need to make sure that we have also PubSub
        self._subscriber = query_utility(IPubSubUtility)
        if self._subscriber is None and settings['updates_channel']:
            raise NoPubSubUtility()
        elif settings['updates_channel'] not in (None, ''):
            await self._subscriber.initialized()
            await self._subscriber.subscribe(settings['updates_channel'], self._uid, self.invalidate)
        self.initialized = True

    async def finalize(self, app):
        settings = app_settings['cache']
        if self._subscriber is not None:
            try:
                await self._subscriber.unsubscribe(settings['updates_channel'], self._uid)
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
                logger.info('Retrieved {} from memory cache'.format(key))
                return self._memory_cache[key]
            if self._obj_driver is not None:
                val = await self._obj_driver.get(CACHE_PREFIX + key)
                if val is not None:
                    logger.info('Retrieved {} from redis cache'.format(key))
                    val = serialize.loads(val)
                    self._memory_cache[key] = val
        except Exception:
            logger.warning('Error getting cache value', exc_info=True)

    def get_size(self, value):
        if isinstance(value, dict):
            if 'state' in value:
                return len(value['state'])
        if isinstance(value, list) and len(value) > 0:
            # if its a list, guesss from first gey the length, and
            # estimate it from the total lenghts on the list..
            return getsizeof(value[0]) * len(value)
        if type(value) in _basic_types:
            return getsizeof(value)
        return _default_size

    # Set a object from cache
    async def set(self, key, value):
        try:
            size = self.get_size(value)
            self._memory_cache.set(key, value, size)
            if self._obj_driver is not None:
                await self._obj_driver.set(
                    CACHE_PREFIX + key,
                    serialize.dumps(value),
                    expire=self._settings.get('ttl', 3600))
            logger.info('set {} in cache'.format(key))
        except Exception:
            logger.warning('Error setting cache value', exc_info=True)

    @profilable
    # Delete a set of objects from cache
    async def delete_all(self, keys):
        delete_keys = []
        for key in keys:
            delete_keys.append(CACHE_PREFIX + key)
            if key in self._memory_cache:
                del self._memory_cache[key]
        if len(delete_keys) > 0 and self._obj_driver is not None:
            await self._obj_driver.delete_all(delete_keys)

    # Delete a set of objects from cache
    async def delete(self, key):
        try:
            if key in self._memory_cache:
                del self._memory_cache[key]
            await self._obj_driver.delete(key)
        except Exception:
            logger.warning('Error removing from cache', exc_info=True)

    # Clean all cache
    async def clear(self):
        try:
            self._memory_cache.clear()
            if self._obj_driver is not None:
                await self._obj_driver.flushall()
            logger.info('Cleared cache')
        except Exception:
            logger.warning('Error clearing cache', exc_info=True)

    @profilable
    # Called by the subscription to invalidations
    async def invalidate(self, *, data=None, sender=None):
        try:
            msg = serialize.loads(data)
        except (TypeError, pickle.UnpicklingError):
            logger.warning("Invalid invalidation message")
            pass

        assert isinstance(msg, dict)
        assert 'tid' in msg
        assert 'keys' in msg
        if msg['tid'] in self._ignored_tids:
            # on the same thread, ignore this sucker...
            self._ignored_tids.remove(msg['tid'])
            return

        mem_cache_obj = memcache.get_memory_cache()
        for key in msg['keys']:
            if key in mem_cache_obj:
                del mem_cache_obj[key]

        for cache_key, ob in msg.get('push', {}).items():
            mem_cache_obj[cache_key] = ob

    def ignore_tid(self, tid):
        # so we don't invalidate twice...
        self._ignored_tids.append(tid)

    async def send_invalidation(self, tid, keys_to_publish, push):
        self.ignore_tid(tid)
        if self._subscriber:
            await self._subscriber.publish(
                self._settings['updates_channel'],
                serialize.dumps({
                    'tid': tid,
                    'keys': keys_to_publish,
                    'push': push
                }))

    @profilable
    async def synchronize(self, stored_objects, keys_to_publish, tid):
        '''
        publish cache changes on redis
        '''
        push = {}
        for obj, pickled in stored_objects:
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

            if ob_key in keys_to_publish:
                keys_to_publish.remove(ob_key)
            push[ob_key] = val

        channel_utility = query_utility(IPubSubUtility)
        if channel_utility is None:
            raise NoPubSubUtility()
        await channel_utility.publish(
            self._settings['updates_channel'], 
            serialize.dumps({
                'tid': tid,
                'keys': keys_to_publish,
                'push': push
            }))

    async def get_stats(self):
        result = {
            'in-memory': {
                'size': len(self._memory_cache),
                'stats': self._memory_cache.get_stats()
            }
        }
        if self._obj_driver is not None:
            result['network']: self.driver.info()
        return result
