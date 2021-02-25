from guillotina.contrib.memcached.driver import MemcachedDriver
from guillotina.contrib.memcached.driver import safe_key
from guillotina.contrib.memcached.driver import update_connection_pool_metrics
from guillotina.utils import resolve_dotted_name
from unittest import mock

import asyncio
import emcache
import pytest


pytestmark = pytest.mark.asyncio


MEMCACHED_SETTINGS = {"applications": ["guillotina", "guillotina.contrib.memcached"]}

MOCK_HOSTS = ["localhost:11211"]


@pytest.fixture(scope="function")
def dont_probe_metrics():
    with mock.patch("guillotina.contrib.memcached.driver._SEND_METRICS", False):
        yield


@pytest.fixture(scope="function")
def mocked_create_client():
    with mock.patch("guillotina.contrib.memcached.driver.emcache.create_client") as create_client:
        f = asyncio.Future()
        f.set_result(None)
        create_client.return_value = f
        yield create_client


async def test_create_client_returns_emcache_client(memcached_container, guillotina_main):
    driver = MemcachedDriver()
    assert driver.client is None
    host, port = memcached_container
    settings = {"hosts": [f"{host}:{port}"]}
    client = await driver._create_client(settings)
    assert isinstance(client, emcache.Client)


async def test_client_is_initialized_with_configured_hosts(mocked_create_client):
    settings = {"hosts": MOCK_HOSTS}
    driver = MemcachedDriver()
    await driver._create_client(settings)
    assert len(mocked_create_client.call_args[0][0]) == 1


async def test_create_client_ignores_invalid_params(mocked_create_client):
    settings = {"hosts": MOCK_HOSTS}
    driver = MemcachedDriver()
    await driver._create_client({"foo": "bar", **settings})
    assert mocked_create_client.call_args[1] == {}


@pytest.mark.parametrize(
    "param,values",
    [
        ("timeout", [1.0, None]),
        ("max_connections", [20]),
        ("min_connections", [2]),
        ("purge_unused_connections_after", [1, None]),
        ("connection_timeout", [20, None]),
        ("purge_unhealthy_nodes", [True]),
    ],
)
async def test_create_client_sets_configured_params(mocked_create_client, param, values):
    for value in values:
        settings = {"hosts": MOCK_HOSTS}
        driver = MemcachedDriver()
        await driver._create_client({**settings, **{param: value}})
        assert mocked_create_client.call_args[1][param] == value


@pytest.mark.app_settings(MEMCACHED_SETTINGS)
async def test_memcached_ops(memcached_container, guillotina_main, dont_probe_metrics):
    driver = await resolve_dotted_name("guillotina.contrib.memcached").get_driver()
    assert driver.initialized
    assert driver.client is not None

    await driver.set("test", b"testdata", expire=10)
    result = await driver.get("test")
    assert result == b"testdata"

    await driver.set("test2", b"testdata", expire=10)
    await driver.set("test3", b"testdata", expire=10)
    await driver.set("test4", b"testdata", expire=1)
    await driver.set("test5", b"testdata", expire=20)

    await driver.delete("test")
    result = await driver.get("test")
    assert result is None

    await driver.delete_all(["test2", "test3"])
    result = await driver.get("test2")
    assert result is None

    await asyncio.sleep(1)
    result = await driver.get("test4")
    assert result is None

    await driver.flushall()
    result = await driver.get("test5")
    assert result is None

    await driver.info()

    await driver.finalize()
    assert driver.initialized is False


unsafe_keys = ["a" * 255, "foo bar", b"\x130".decode()]


@pytest.mark.app_settings(MEMCACHED_SETTINGS)
@pytest.mark.parametrize("unsafe_key", unsafe_keys)
async def test_memcached_ops_are_safe_key(
    memcached_container, guillotina_main, unsafe_key, dont_probe_metrics
):
    driver = await resolve_dotted_name("guillotina.contrib.memcached").get_driver()
    await driver.get(unsafe_key)
    await driver.set(unsafe_key, b"foo")
    await driver.delete(unsafe_key)
    await driver.delete_all([unsafe_key])


@pytest.mark.parametrize("unsafe_key", unsafe_keys)
async def test_safe_key(unsafe_key):
    key = safe_key(unsafe_key)
    assert isinstance(key, bytes)
    assert len(key) < 250
    for char in key:
        assert char >= 33
        assert char <= 126


async def test_delete_all():
    with mock.patch("guillotina.contrib.memcached.driver.watch") as watch_mocked:
        with mock.patch("guillotina.contrib.memcached.driver.MEMCACHED_OPS_DELETE_ALL_NUM_KEYS") as all_keys:
            driver = MemcachedDriver()
            driver._client = mock.Mock()
            await driver.delete_all(["foo", "bar"])
            watch_mocked.assert_called()
            all_keys.observe.assert_called_with(2)
            driver._client.delete.assert_has_calls(
                [mock.call(safe_key("foo"), noreply=True), mock.call(safe_key("bar"), noreply=True)]
            )


async def test_delete_all_empty_keys():
    with mock.patch("guillotina.contrib.memcached.driver.watch") as watch_mocked:
        with mock.patch("guillotina.contrib.memcached.driver.MEMCACHED_OPS_DELETE_ALL_NUM_KEYS") as all_keys:
            driver = MemcachedDriver()
            driver._client = mock.Mock()
            await driver.delete_all([])
            all_keys.observe.assert_not_called()
            watch_mocked.assert_not_called()


class TestUpdateConnectionPoolMetrics:
    @pytest.fixture
    def avg(self):
        with mock.patch("guillotina.contrib.memcached.driver.MEMCACHED_CREATE_CONNECTION_AVG") as _avg:
            yield _avg

    @pytest.fixture
    def p50(self):
        with mock.patch("guillotina.contrib.memcached.driver.MEMCACHED_CREATE_CONNECTION_P50") as _p50:
            yield _p50

    @pytest.fixture
    def p99(self):
        with mock.patch("guillotina.contrib.memcached.driver.MEMCACHED_CREATE_CONNECTION_P99") as _p99:
            yield _p99

    @pytest.fixture
    def upper(self):
        with mock.patch("guillotina.contrib.memcached.driver.MEMCACHED_CREATE_CONNECTION_UPPER") as _upper:
            yield _upper

    @pytest.fixture
    async def metrics(self):
        metrics = mock.Mock()
        metrics.cur_connections = 1
        metrics.connections_created = 1
        metrics.connections_created_with_error = 0
        metrics.connections_purged = 0
        metrics.connections_closed = 0
        metrics.operations_executed = 1
        metrics.operations_executed_with_error = 0
        metrics.operations_waited = 0
        metrics.create_connection_avg = 10.0
        metrics.create_connection_p50 = 50.0
        metrics.create_connection_p99 = 99.0
        metrics.create_connection_upper = 100.0
        return metrics

    async def test_updated_connection_pool_metrics_create_connection_latencies(
        self, avg, p50, p99, upper, metrics
    ):
        node_metrics = {"node1": metrics}
        last_state = {"node1": metrics}
        client = mock.Mock()
        client.cluster_managment.return_value.connection_pool_metrics.return_value = node_metrics

        update_connection_pool_metrics(client, last_state)

        avg.assert_has_calls([mock.call.labels(node="node1"), mock.call.labels().set(10.0)])
        p50.assert_has_calls([mock.call.labels(node="node1"), mock.call.labels().set(50.0)])
        p99.assert_has_calls([mock.call.labels(node="node1"), mock.call.labels().set(99.0)])
        upper.assert_has_calls([mock.call.labels(node="node1"), mock.call.labels().set(100.0)])

    async def test_updated_connection_pool_metrics_create_connection_latencies_none(
        self, avg, p50, p99, upper, metrics
    ):
        # Override default fixture values for simulating that latencies do not have
        # values yet.
        metrics.create_connection_avg = None
        metrics.create_connection_p50 = None
        metrics.create_connection_p99 = None
        metrics.create_connection_upper = None

        node_metrics = {"node1": metrics}
        last_state = {"node1": metrics}
        client = mock.Mock()
        client.cluster_managment.return_value.connection_pool_metrics.return_value = node_metrics

        update_connection_pool_metrics(client, last_state)

        avg.assert_not_called()
        p50.assert_not_called()
        p99.assert_not_called()
        upper.assert_not_called()
