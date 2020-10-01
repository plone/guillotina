try:
    import emcache
except ImportError:
    print("If you add guillotina.contrib.memcached you need to add emcache on your requirements")
    raise

from guillotina import app_settings
from guillotina import metrics
from guillotina.contrib.memcached.exceptions import NoMemcachedConfigured
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import asyncio
import backoff
import logging


try:
    import prometheus_client

    MEMCACHED_OPS = prometheus_client.Counter(
        "guillotina_cache_memcached_ops_total",
        "Total count of ops by type of operation and the error if there was.",
        labelnames=["type", "error"],
    )
    MEMCACHED_OPS_PROCESSING_TIME = prometheus_client.Histogram(
        "guillotina_cache_memcached_ops_processing_time_seconds",
        "Histogram of operations processing time by type (in seconds)",
        labelnames=["type"],
    )

    class watch(metrics.watch):
        def __init__(self, operation: str):
            super().__init__(
                counter=MEMCACHED_OPS,
                histogram=MEMCACHED_OPS_PROCESSING_TIME,
                labels={"type": operation},
                error_mappings={"timeout": asyncio.TimeoutError},
            )


except ImportError:
    watch = metrics.watch  # type: ignore


logger = logging.getLogger("guillotina.contrib.memcached")


class MemcachedDriver:
    """
    Implements a cache driver using Memcached
    """

    def __init__(self):
        self._client: Optional[emcache.Client] = None
        self.initialized: bool = False
        self.init_lock = asyncio.Lock()

    @property
    def client(self) -> Optional[emcache.Client]:
        return self._client

    def _get_client(self) -> emcache.Client:
        if self._client is None:
            raise NoMemcachedConfigured("Memcached client not initialized")
        return self._client

    async def initialize(self, loop):
        async with self.init_lock:
            if self.initialized is False:
                try:
                    await self._connect()
                    self.initialized = True
                except Exception:  # pragma: no cover
                    logger.error("Error initializing memcached driver", exc_info=True)

    async def _create_client(self, settings: Dict[str, Any]) -> emcache.Client:
        hosts = settings.get("hosts")
        if hosts is None or len(hosts) == 0:
            raise NoMemcachedConfigured("No hosts configured")

        # expected hosts format: ["server1:11211", "server2:11211", ...]
        servers = [
            emcache.MemcachedHostAddress(host, int(port)) for host, port in map(lambda x: x.split(":"), hosts)
        ]
        # Configure client constructor from settings
        client_params = {}
        for param in [
            "timeout",
            "max_connections",
            "purge_unused_connections_after",
            "connection_timeout",
            "purge_unhealthy_nodes",
        ]:
            if param in settings and settings[param] is not None:
                client_params[param] = settings[param]
        with watch("connect"):
            return await emcache.create_client(servers, **client_params)

    @backoff.on_exception(backoff.expo, (OSError,), max_time=30, max_tries=4)
    async def _connect(self):
        try:
            settings = app_settings["memcached"]
        except KeyError:
            raise NoMemcachedConfigured("Memcached settings not found")
        self._client = await self._create_client(settings)

    async def finalize(self):
        if self._client is not None:
            await self._client.close()
        self.initialized = False

    async def info(self):
        # emcache client does not support getting stats yet
        return None

    # VALUE API

    async def set(self, key: str, data: bytes, *, expire: Optional[int] = None) -> None:
        client = self._get_client()
        kwargs: Dict[str, int] = {}
        if expire is not None:
            kwargs["exptime"] = expire
        with watch("set"):
            await client.set(key.encode(), data, **kwargs)

    async def get(self, key: str) -> Optional[bytes]:
        client = self._get_client()
        with watch("get") as w:
            item: Optional[emcache.Item] = await client.get(key.encode())
            if item is None:
                # cache miss
                w.labels["type"] = "get_miss"
                return None
            else:
                # cache hit
                return item.value

    async def delete(self, key: str) -> None:
        client = self._get_client()
        with watch("delete"):
            await client.delete(key.encode(), noreply=True)

    async def delete_all(self, keys: List[str]) -> None:
        client = self._get_client()
        with watch("delete_many"):
            for key in keys:
                try:
                    with watch("delete"):
                        await client.delete(key.encode(), noreply=True)
                    logger.debug("Deleted cache keys {}".format(keys))
                except Exception:
                    logger.warning("Error deleting cache keys {}".format(keys), exc_info=True)

    async def flushall(self) -> None:
        client = self._get_client()
        # Flush all nodes
        for node in client.cluster_managment().nodes():
            with watch("flush"):
                await client.flush_all(node)
