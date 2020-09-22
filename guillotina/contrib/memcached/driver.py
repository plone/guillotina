try:
    import emcache
    import emcache.client_errors
except ImportError:
    print("If you add guillotina.contrib.memcached you need to add pfreixes/emcache on your requirements")
    raise

from guillotina import app_settings
from guillotina.contrib.memcached.exceptions import NoMemcachedConfigured
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import asyncio
import backoff
import logging


logger = logging.getLogger("guillotina.contrib.memcached")


class MemcachedDriver:
    """
    Implements a cache driver using Memcached
    """

    def __init__(self):
        self._client: Optional[emcache.Client] = None
        self.initialized: bool = False
        self.init_lock = asyncio.Lock()

    async def initialize(self, loop):
        async with self.init_lock:
            if self.initialized is False:
                while True:
                    try:
                        await self._connect()
                        self.initialized = True
                        break
                    except Exception:  # pragma: no cover
                        logger.error("Error initializing pubsub", exc_info=True)

    @backoff.on_exception(backoff.expo, (OSError,), max_time=30, max_tries=4)
    async def _connect(self):
        settings = app_settings["memcached"]
        hosts = [emcache.MemcachedHostAddress(host, port) for host, port in settings["hosts"]]
        timeout = settings.get("timeout")
        max_connections = settings.get("max_connections")
        self._client = await emcache.create_client(hosts, timeout=timeout, max_connections=max_connections)

    async def finalize(self):
        if self._client is not None:
            self._client.close()
        self.initialized = False

    # VALUE API

    async def set(self, key: str, data: str, *, expire: Optional[int] = None) -> None:
        if self._client is None:
            raise NoMemcachedConfigured()

        kwargs: Dict[Any] = {}
        if expire is not None:
            kwargs["exptime"] = expire

        await self._client.set(key.encode(), data.encode(), **kwargs)

    async def get(self, key: str) -> Optional[str]:
        if self._client is None:
            raise NoMemcachedConfigured()

        item: Optional[emcache.Item] = await self._client.get(key)
        if item is not None:
            return item.value.decode()
        else:
            return None

    async def delete(self, key: str) -> None:
        if self._client is None:
            raise NoMemcachedConfigured()

        await self._client.delete(key.encode())

    async def delete_all(self, keys: List[str]) -> None:
        if self._client is None:
            raise NoMemcachedConfigured()

        for key in keys:
            try:
                await self._client.delete(key.encode())
                logger.debug("Deleted cache keys {}".format(keys))
            except Exception:
                logger.warning("Error deleting cache keys {}".format(keys), exc_info=True)

    async def flushall(self) -> None:
        if self._client is None:
            raise NoMemcachedConfigured()

        # Flush all nodes
        for node in self._client.cluster_managment.nodes():
            await self._client.flush_all(node.memcached_host_address)
