from asyncmock import AsyncMock
from guillotina.contrib.memcached.driver import MemcachedDriver


class TestMemcachedMetrics:
    async def test_connect_metric(self, metrics_registry):
        driver = MemcachedDriver()
        driver._client = AsyncMock()
        await driver.initialize(None)
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memcached_ops_total", {"type": "connect", "error": "none"}
            )
            == 1.0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memcached_ops_processing_time_seconds_sum", {"type": "connect"}
            )
            > 0
        )

    async def test_set_memcached_metric(self, metrics_registry):
        driver = MemcachedDriver()
        driver._client = AsyncMock()
        await driver.set("foo", "bar")

        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memcached_ops_total", {"type": "set", "error": "none"}
            )
            == 1.0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memcached_ops_processing_time_seconds_sum", {"type": "set"}
            )
            > 0
        )

    async def test_get_memcached_metric(self, metrics_registry):
        driver = MemcachedDriver()
        driver._client = AsyncMock()
        await driver.get("foo")
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memcached_ops_total", {"type": "get", "error": "none"}
            )
            == 1.0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memcached_ops_processing_time_seconds_sum", {"type": "get"}
            )
            > 0
        )

    async def test_delete_memcached_metric(self, metrics_registry):
        driver = MemcachedDriver()
        driver._client = AsyncMock()
        await driver.delete("foo")
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memcached_ops_total", {"type": "delete", "error": "none"}
            )
            == 1.0
        )
        assert (
            metrics_registry.get_sample_value(
                "guillotina_cache_memcached_ops_processing_time_seconds_sum", {"type": "delete"}
            )
            > 0
        )
