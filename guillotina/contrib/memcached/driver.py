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
import copy
import hashlib
import logging


try:
    import prometheus_client
    from prometheus_client.utils import INF

    _SEND_METRICS = True

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
    MEMCACHED_OPS_DELETE_ALL_NUM_KEYS = prometheus_client.Histogram(
        "guillotina_cache_memcached_delete_all_num_keys",
        "Histogram of number of keys deleted at each delete all call",
        buckets=(1, 2, 4, 10, 20, 50, 100, INF),
    )

    MEMCACHED_CURRENT_CONNECTIONS = prometheus_client.Gauge(
        "guillotina_cache_memcached_node_current_connections",
        "Total number of opened connections per node",
        labelnames=["node"],
    )

    MEMCACHED_CONNECTIONS_CREATED = prometheus_client.Counter(
        "guillotina_cache_memcached_node_connections_created",
        "How many node connections have been created",
        labelnames=["node"],
    )

    MEMCACHED_CONNECTIONS_CREATED_WITH_ERROR = prometheus_client.Counter(
        "guillotina_cache_memcached_node_connections_created_with_error",
        "How many node connections have been created with error",
        labelnames=["node"],
    )

    MEMCACHED_CONNECTIONS_PURGED = prometheus_client.Counter(
        "guillotina_cache_memcached_node_connections_purged",
        "How many node connections have been purged",
        labelnames=["node"],
    )

    MEMCACHED_CONNECTIONS_CLOSED = prometheus_client.Counter(
        "guillotina_cache_memcached_node_connections_closed",
        "How many node connections have been closed",
        labelnames=["node"],
    )

    MEMCACHED_NODE_OPS_EXECUTED = prometheus_client.Counter(
        "guillotina_cache_memcached_node_operations_executed",
        "How many node operations have been executed",
        labelnames=["node"],
    )

    MEMCACHED_NODE_OPS_EXECUTED_WITH_ERROR = prometheus_client.Counter(
        "guillotina_cache_memcached_node_operations_executed_with_error",
        "How many node operations have been executed with error",
        labelnames=["node"],
    )

    MEMCACHED_NODE_OPS_WAITED = prometheus_client.Counter(
        "guillotina_cache_memcached_node_operations_waited",
        "How many node operations have been waited",
        labelnames=["node"],
    )

    class watch(metrics.watch):
        def __init__(self, operation: str):
            super().__init__(
                counter=MEMCACHED_OPS,
                histogram=MEMCACHED_OPS_PROCESSING_TIME,
                labels={"type": operation},
                error_mappings={"timeout": asyncio.TimeoutError, "cancelled": asyncio.CancelledError},
            )


except ImportError:
    _SEND_METRICS = False
    watch = metrics.dummy_watch  # type: ignore


logger = logging.getLogger("guillotina.contrib.memcached")


def safe_key(key: str) -> bytes:
    """This is needed because memcached servers do not support keys longer
    than 250 bytes, or keys with control characters or whitespaces.

    """
    return hashlib.sha224(key.encode()).hexdigest().encode()


class MemcachedDriver:
    """
    Implements a cache driver using Memcached
    """

    def __init__(self):
        self._client: Optional[emcache.Client] = None
        self.initialized: bool = False
        self.init_lock = asyncio.Lock()
        self._metrics_task = None

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

                if _SEND_METRICS:
                    self._metrics_task = loop.create_task(metrics_probe(self.client))

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
        if self._metrics_task is not None and not self._metrics_task.cancelled():
            self._metrics_task.cancel()
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
            await client.set(safe_key(key), data, **kwargs)

    async def get(self, key: str) -> Optional[bytes]:
        client = self._get_client()
        with watch("get") as w:
            item: Optional[emcache.Item] = await client.get(safe_key(key))
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
            await client.delete(safe_key(key), noreply=True)

    async def delete_all(self, keys: List[str]) -> None:
        if len(keys) == 0:
            return

        if _SEND_METRICS:
            MEMCACHED_OPS_DELETE_ALL_NUM_KEYS.observe(len(keys))

        client = self._get_client()
        with watch("delete_many"):
            for key in keys:
                try:
                    with watch("delete"):
                        await client.delete(safe_key(key), noreply=True)
                    logger.debug("Deleted cache keys {}".format(keys))
                except Exception:
                    logger.warning("Error deleting cache keys {}".format(keys), exc_info=True)

    async def flushall(self) -> None:
        client = self._get_client()
        # Flush all nodes
        for node in client.cluster_managment().nodes():
            with watch("flush"):
                await client.flush_all(node)


async def metrics_probe(client: emcache.Client, every: int = 30):
    """Periodically updates memcached cluster nodes metrics.

    :param every: interval in seconds at which metrics are updated

    """
    state: Optional[emcache.ConnectionPoolMetrics] = None
    while True:
        state = await update_connection_pool_metrics(client, state)
        await asyncio.sleep(every)


async def update_connection_pool_metrics(
    client: emcache.Client, last_state: Optional[emcache.ConnectionPoolMetrics] = None
) -> emcache.ConnectionPoolMetrics:

    # Every node will have it's own label
    metrics = client.cluster_managment().connection_pool_metrics()
    for node, node_metrics in metrics.items():
        if last_state is None:
            # Wait until we have previous state
            break
        node_label = str(node)
        MEMCACHED_CURRENT_CONNECTIONS.labels(node=node_label).set(node_metrics.cur_connections)
        # Update counters
        for counter, attr in {
            MEMCACHED_CONNECTIONS_CREATED: "connections_created",
            MEMCACHED_CONNECTIONS_CREATED_WITH_ERROR: "connections_created_with_error",
            MEMCACHED_CONNECTIONS_PURGED: "connections_purged",
            MEMCACHED_CONNECTIONS_CLOSED: "connections_closed",
            MEMCACHED_NODE_OPS_EXECUTED: "operations_executed",
            MEMCACHED_NODE_OPS_EXECUTED_WITH_ERROR: "operations_executed_with_error",
            MEMCACHED_NODE_OPS_WAITED: "operations_waited",
        }.items():
            try:
                prev_value = getattr(last_state[node], attr)
            except KeyError:
                # No previous metrics for that node
                continue
            current_value = getattr(node_metrics, attr)
            counter.labels(node=node_label).inc(current_value - prev_value)

    return copy.deepcopy(metrics)
