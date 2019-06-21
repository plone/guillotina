try:
    import aioredis
except ImportError:
    print("If you add guillotina.contrib.redis you need to add aioredis on your requirements")
    raise

import asyncio
import logging
from guillotina import app_settings
from guillotina.contrib.redis.exceptions import NoRedisConfigured
from typing import List
from typing import Optional

logger = logging.getLogger('guillotina.contrib.redis')


class RedisDriver:

    def __init__(self):
        self._pool = None
        self._pubsub = None
        self._loop = None
        self._receivers = {}
        self.initialized = False
        self.init_lock = asyncio.Lock()

    async def initialize(self, loop):
        self._loop = loop
        async with self.init_lock:
            if self.initialized is False:
                try:
                    settings = app_settings['redis']
                    self._pool = await aioredis.create_pool(
                        (settings['host'], settings['port']),
                        **settings['pool'],
                        loop=loop)
                    self._pubsub_subscriptor = aioredis.Redis(await self._pool.acquire())
                    self.initialized = True
                except AssertionError:
                    logger.error("Error on initializing redis", exc_info=True)

    async def finalize(self):
        if self._pool is not None:
            self._pool.close()
        await self._pool.wait_closed()
        self.initialized = False

    async def info(self):
        return await self._pool.execute(b'COMMAND', b'INFO', 'get')

    # VALUE API

    async def set(self, key: str, data: str, *, expire: Optional[int] = None):
        if self._pool is None:
            raise NoRedisConfigured()
        args = []
        if expire is not None:
            args[:] = [b'EX', expire]
        ok = await self._pool.execute(b'SET', key, data, *args)
        assert ok == b'OK', ok

    async def get(self, key: str) -> str:
        if self._pool is None:
            raise NoRedisConfigured()
        return await self._pool.execute(b'GET', key)

    async def delete(self, key: str):
        if self._pool is None:
            raise NoRedisConfigured()
        await self._pool.execute(b'DEL', key)

    async def delete_all(self, keys: List[str]):
        if self._pool is None:
            raise NoRedisConfigured()
        for key in keys:
            try:
                await self._pool.execute(b'DEL', key)
                logger.info('Deleted cache keys {}'.format(keys))
            except Exception:
                logger.warning('Error deleting cache keys {}'.format(
                    keys), exc_info=True)

    async def flushall(self, *, async_op: Optional[bool] = False):
        if self._pool is None:
            raise NoRedisConfigured()
        ops = [b'FLUSHDB']
        if async_op:
            ops.append(b'ASYNC')
        await self._pool.execute(*ops)

    # PUBSUB API

    async def publish(self, channel_name: str, data: str):
        if self._pool is None:
            raise NoRedisConfigured()
        await self._pool.execute(b'publish', channel_name, data)

    async def unsubscribe(self, channel_name: str):
        if self._pubsub_subscriptor is None:
            raise NoRedisConfigured()
        await self._pubsub_subscriptor.unsubscribe(channel_name)

    async def subscribe(self, channel_name: str):
        if self._pubsub_subscriptor is None:
            raise NoRedisConfigured()
        channel, = await self._pubsub_subscriptor.subscribe(channel_name)
        return self._listener(channel)

    async def _listener(self, channel: aioredis.Channel):
        while (await channel.wait_message()):
            msg = await channel.get()
            yield msg


