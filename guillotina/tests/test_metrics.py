from asyncmock import AsyncMock
from guillotina import metrics
from guillotina.const import ROOT_ID
from guillotina.content import Container
from guillotina.contrib.cache import memcache
from guillotina.contrib.cache.utility import CacheUtility
from guillotina.contrib.redis.driver import RedisDriver
from guillotina.db import transaction
from guillotina.db.storages.pg import PostgresqlStorage
from guillotina.db.transaction import Transaction
from guillotina.db.transaction_manager import TransactionManager
from guillotina.tests.utils import create_content
from unittest.mock import MagicMock

import asyncio
import pickle
import prometheus_client
import pytest


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

    async def test_delete_many_redis_metric(self, metrics_registry):
        driver = RedisDriver()
        driver._pool = AsyncMock()
        await driver.delete_all(["foo", "bar"])
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_redis_ops_total", {"type": "delete_many", "error": "none"}
            )
            == 1.0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_redis_ops_processing_time_seconds_sum", {"type": "delete_many"}
            )
            > 0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_redis_ops_total", {"type": "delete", "error": "none"}
            )
            == 2.0
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


async def test_lock_metric():
    lock = asyncio.Lock()
    metric = prometheus_client.Histogram("test_metric", "Test")
    assert metric.collect()[0].samples[0].value == 0
    async with metrics.watch_lock(lock, metric):
        assert lock.locked()
    assert not lock.locked()
    assert metric.collect()[0].samples[0].value == 1

    # Should not lock if there is no histogram to record to
    async with metrics.watch_lock(lock, histogram=None):
        assert not lock.locked()


async def test_dummy_watch():
    watch = metrics.dummy_watch("operation")
    assert watch.counter is None
    assert watch.histogram is None
    assert watch.labels == {}
    assert watch.error_mappings == {}


class TestTransactionMetrics:
    async def test_record_transaction_cache_hit(self, dummy_guillotina, metrics_registry):
        storage = AsyncMock()
        mng = TransactionManager(storage)
        cache = AsyncMock()
        cache.get.return_value = {
            "state": pickle.dumps(create_content()),
            "zoid": "foobar",
            "tid": 1,
            "id": "foobar",
        }
        strategy = AsyncMock()
        txn = Transaction(mng, cache=cache, strategy=strategy)

        await txn.get("foobar")

        assert (
            metrics_registry.get_sample_value("guillotina_cache_ops_total", {"type": "_get", "result": "hit"})
            == 1.0
        )

    async def test_record_transaction_cache_hit_container(self, dummy_guillotina, metrics_registry):
        storage = AsyncMock()
        mng = TransactionManager(storage)
        cache = AsyncMock()

        cache.get.return_value = {
            "state": pickle.dumps(create_content(Container)),
            "zoid": ROOT_ID,
            "tid": 1,
            "id": "foobar",
        }
        strategy = AsyncMock()
        txn = Transaction(mng, cache=cache, strategy=strategy)

        await txn.get("foobar")

        assert (
            metrics_registry.get_sample_value("guillotina_cache_ops_total", {"type": "_get", "result": "hit"})
            is None
        )

        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_ops_total", {"type": "_get", "result": "hit_roots"}
            )
            == 1.0
        )

    async def test_record_transaction_cache_miss(self, dummy_guillotina, metrics_registry):
        storage = AsyncMock()
        storage.load.return_value = {
            "state": pickle.dumps(create_content()),
            "zoid": "foobar",
            "tid": 1,
            "id": "foobar",
        }
        mng = TransactionManager(storage)
        cache = AsyncMock()
        cache.get.return_value = None

        strategy = AsyncMock()
        txn = Transaction(mng, cache=cache, strategy=strategy)

        await txn.get("foobar")

        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_ops_total", {"type": "_get", "result": "miss"}
            )
            == 1.0
        )

    async def test_record_transaction_cache_hit_get_child(self, dummy_guillotina, metrics_registry):
        storage = AsyncMock()
        mng = TransactionManager(storage)
        cache = AsyncMock()

        cache.get.return_value = {
            "state": pickle.dumps(create_content()),
            "zoid": "foobar",
            "tid": 1,
            "id": "foobar",
        }
        strategy = AsyncMock()
        txn = Transaction(mng, cache=cache, strategy=strategy)

        ob = create_content()
        await txn.get_child(ob, "foobar")

        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_ops_total", {"type": "_get_child", "result": "hit"}
            )
            == 1.0
        )

    async def test_record_transaction_cache_hit_get_child_root(self, dummy_guillotina, metrics_registry):
        storage = AsyncMock()
        mng = TransactionManager(storage)
        cache = AsyncMock()

        cache.get.return_value = {
            "state": pickle.dumps(create_content()),
            "zoid": "foobar",
            "tid": 1,
            "id": "foobar",
        }
        strategy = AsyncMock()
        txn = Transaction(mng, cache=cache, strategy=strategy)

        ob = create_content(Container)
        await txn.get_child(ob, "foobar")

        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_ops_total", {"type": "_get_child", "result": "hit_roots"}
            )
            == 1.0
        )

    async def test_record_transaction_cache_empty(self, dummy_guillotina, metrics_registry):
        storage = AsyncMock()
        mng = TransactionManager(storage)
        cache = AsyncMock()

        cache.get.return_value = transaction._EMPTY
        strategy = AsyncMock()
        txn = Transaction(mng, cache=cache, strategy=strategy)

        ob = create_content(Container)
        with pytest.raises(KeyError):
            await txn.get_annotation(ob, "foobar")

        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_ops_total", {"type": "_get_annotation", "result": "hit_empty"}
            )
            == 1.0
        )


class TestInMemoryMetrics:
    @pytest.fixture
    async def cache_utility(self, dummy_guillotina):
        memcache._lru = None
        util = CacheUtility()
        await util.initialize()
        yield util
        await util.finalize()

    @pytest.mark.app_settings({"cache": {"memory_cache_size": 1024}})
    async def test_record_cache_hit(self, cache_utility, metrics_registry):
        cache_utility._memory_cache["foobar"] = "foobar"
        assert await cache_utility.get("foobar") == "foobar"
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memory_ops_total", {"type": "get", "result": "hit"}
            )
            == 1.0
        )

    @pytest.mark.app_settings({"cache": {"memory_cache_size": 1024}})
    async def test_record_cache_miss(self, cache_utility, metrics_registry):
        assert await cache_utility.get("foobar") is None
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memory_ops_total", {"type": "get", "result": "miss"}
            )
            == 1.0
        )

    @pytest.mark.app_settings({"cache": {"memory_cache_size": 1024}})
    async def test_record_cache_set(self, cache_utility, metrics_registry):
        await cache_utility.set("foobar", "foobar")
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memory_ops_total", {"type": "set", "result": "none"}
            )
            == 1.0
        )

    @pytest.mark.app_settings({"cache": {"memory_cache_size": 1024}})
    async def test_record_cache_delete(self, cache_utility, metrics_registry):
        await cache_utility.delete("foobar")
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memory_ops_total", {"type": "delete", "result": "miss"}
            )
            == 1.0
        )

        cache_utility._memory_cache["foobar"] = "foobar"
        await cache_utility.delete("foobar")
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memory_ops_total", {"type": "delete", "result": "hit"}
            )
            == 1.0
        )

    @pytest.mark.app_settings({"cache": {"memory_cache_size": 1024}})
    async def test_record_cache_evicted(self, cache_utility, metrics_registry):
        cache = memcache.get_memory_cache()
        cache.set("foobar", "X" * 1023, 1023)
        cache.set("foobar2", "X" * 1023, 1023)
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memory_ops_total", {"type": "evicted", "result": "none"}
            )
            == 1.0
        )

    @pytest.mark.app_settings({"cache": {"memory_cache_size": 1024}})
    async def test_record_cache_size(self, cache_utility, metrics_registry):
        value = "X" * 1023
        keys = ["foo", "bar", "ba"]

        previous_value = metrics_registry.get_sample_value("guillotina_cache_record_size_sum")

        await cache_utility.set(keys, value)

        current_value = metrics_registry.get_sample_value("guillotina_cache_record_size_sum")
        assert int(current_value - previous_value) == cache_utility.get_size(value) * len(keys)
