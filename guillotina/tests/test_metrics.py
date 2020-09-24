from asyncmock import AsyncMock
from guillotina import metrics
from guillotina.contrib.redis.driver import RedisDriver
from guillotina.db.storages.pg import PostgresqlStorage
from unittest.mock import MagicMock

import asyncio
import prometheus_client


class TestRedisMetrics:
    async def test_set_redis_metric(self, metrics_registry):
        driver = RedisDriver()
        driver._pool = AsyncMock()
        driver._pool.execute.return_value = b"OK"
        await driver.set("foo", "bar")

        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_redis_ops_total", {"type": "set", "error": "none"}
            )
            == 1.0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_redis_ops_processing_time_seconds_sum", {"type": "set"}
            )
            > 0
        )

    async def test_get_redis_metric(self, metrics_registry):
        driver = RedisDriver()
        driver._pool = AsyncMock()
        await driver.get("foo")
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_redis_ops_total", {"type": "get", "error": "none"}
            )
            == 1.0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_redis_ops_processing_time_seconds_sum", {"type": "get"}
            )
            > 0
        )

    async def test_get_miss_redis_metric(self, metrics_registry):
        driver = RedisDriver()
        driver._pool = AsyncMock()
        driver._pool.execute.return_value = None
        await driver.get("foo")
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_redis_ops_total", {"type": "get_miss", "error": "none"}
            )
            == 1.0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_redis_ops_processing_time_seconds_sum", {"type": "get_miss"}
            )
            > 0
        )

    async def test_delete_redis_metric(self, metrics_registry):
        driver = RedisDriver()
        driver._pool = AsyncMock()
        await driver.delete("foo")
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_redis_ops_total", {"type": "delete", "error": "none"}
            )
            == 1.0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_redis_ops_processing_time_seconds_sum", {"type": "delete"}
            )
            > 0
        )


class TestPGMetrics:
    def _make_txn(self):
        mock = AsyncMock()
        mock.lock = mock._lock = asyncio.Lock()
        return mock

    async def test_load_object(self, metrics_registry):
        storage = PostgresqlStorage()
        await storage.load(self._make_txn(), "foobar")
        assert (
            metrics_registry.get_sample_value(
                "guillotina_db_pg_ops_total", {"type": "load_object_by_oid", "error": "none"}
            )
            == 1.0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_db_pg_ops_processing_time_seconds_sum", {"type": "load_object_by_oid"}
            )
            > 0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_db_pg_lock_time_seconds_sum", {"type": "load_object_by_oid"}
            )
            > 0
        )

    async def test_store_object(self, metrics_registry):
        storage = PostgresqlStorage(store_json=False)
        ob = MagicMock()
        ob.__new_marker__ = False
        ob.__serial__ = 1
        txn = self._make_txn()
        txn.get_connection.return_value.fetch.return_value = [{"count": 1}]
        await storage.store("foobar", 1, MagicMock(), ob, txn)
        assert (
            metrics_registry.get_sample_value(
                "guillotina_db_pg_ops_total", {"type": "store_object", "error": "none"}
            )
            == 1.0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_db_pg_ops_processing_time_seconds_sum", {"type": "store_object"}
            )
            > 0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_db_pg_lock_time_seconds_sum", {"type": "store_object"}
            )
            > 0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_db_pg_lock_time_seconds_sum", {"type": "store_object"}
            )
            > 0
        )

    async def test_delete_object(self, metrics_registry):
        storage = PostgresqlStorage(autovacuum=False)
        await storage.delete(self._make_txn(), "foobar")
        assert (
            metrics_registry.get_sample_value(
                "guillotina_db_pg_ops_total", {"type": "delete_object", "error": "none"}
            )
            == 1.0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_db_pg_ops_processing_time_seconds_sum", {"type": "delete_object"}
            )
            > 0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_db_pg_lock_time_seconds_sum", {"type": "delete_object"}
            )
            > 0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_db_pg_lock_time_seconds_sum", {"type": "delete_object"}
            )
            > 0
        )


class TestLock:
    async def test_lock_metric(self):
        lock = asyncio.Lock()
        metric = prometheus_client.Histogram("test_metric", "Test",)
        assert metric.collect()[0].samples[0].value == 0
        async with metrics.watch_lock(metric, lock):
            assert lock.locked()
        assert not lock.locked()
        assert metric.collect()[0].samples[0].value == 1
