from guillotina import configure
from guillotina import metrics
from guillotina.contrib.redis import get_driver
from guillotina.files.adapter import DBDataManager
from guillotina.interfaces import IExternalFileStorageManager
from guillotina.interfaces import IUploadDataManager
from guillotina.renderers import GuillotinaJSONEncoder
from guillotina.transactions import get_transaction

import json
import time


try:
    import prometheus_client

    REDIS_OPS = prometheus_client.Counter(
        "guillotina_dm_redis_ops_total",
        "Total count of ops by type of operation and the error if there was.",
        labelnames=["type", "error"],
    )
    REDIS_OPS_PROCESSING_TIME = prometheus_client.Histogram(
        "guillotina_dm_redis_ops_processing_time_seconds",
        "Histogram of operations processing time by type (in seconds)",
        labelnames=["type"],
    )

    class watch(metrics.watch):
        def __init__(self, operation: str):
            super().__init__(
                counter=REDIS_OPS, histogram=REDIS_OPS_PROCESSING_TIME, labels={"type": operation}
            )


except ImportError:
    watch = metrics.dummy_watch  # type: ignore


@configure.adapter(for_=IExternalFileStorageManager, provides=IUploadDataManager, name="redis")
class RedisFileDataManager(DBDataManager):

    _data = None
    _redis = None
    _loaded = False
    _ttl = 60 * 50 * 5  # 5 minutes should be plenty of time between activity

    async def load(self):
        # preload data
        if self._data is None:
            redis = await self.get_redis()
            key = self.get_key()
            with watch("get"):
                data = await redis.get(key)
            if not data:
                self._data = {}
            else:
                self._loaded = True
                self._data = json.loads(data)

    async def start(self):
        self.protect()
        self._data.clear()

    async def save(self):
        txn = get_transaction()
        txn.add_after_commit_hook(self._save)

    async def _save(self):
        redis = await self.get_redis()
        key = self.get_key()
        self._data["last_activity"] = time.time()
        value = json.dumps(self._data, cls=GuillotinaJSONEncoder)
        with watch("set"):
            await redis.set(key, value, expire=self._ttl)

    async def get_redis(self):
        if self._redis is None:
            self._redis = await get_driver()
        return self._redis

    def get_key(self):
        # only need 1 write to save upload object id...
        return "redisdm-{}-{}".format(self.context.__uuid__, self.field.__name__)

    async def update(self, **kwargs):
        self._data.update(kwargs)

    async def finish(self, values=None):
        val = await super().finish(values=values)
        txn = get_transaction()
        txn.add_after_commit_hook(self._delete_key)
        return val

    async def _delete_key(self):
        # and clear the cache key
        redis = await self.get_redis()
        key = self.get_key()
        with watch("delete"):
            await redis.delete(key)
