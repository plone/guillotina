from guillotina.contrib.memcached.driver import MemcachedDriver
from guillotina.contrib.memcached.driver import safe_key
from guillotina.utils import resolve_dotted_name
from unittest import mock

import asyncio
import emcache
import pytest


pytestmark = pytest.mark.asyncio


MEMCACHED_SETTINGS = {"applications": ["guillotina", "guillotina.contrib.memcached"]}

MOCK_HOSTS = ["localhost:11211"]


@pytest.fixture(scope="function")
def mocked_create_client(loop):
    with mock.patch("guillotina.contrib.memcached.driver.emcache.create_client") as create_client:
        f = asyncio.Future()
        f.set_result(None)
        create_client.return_value = f
        yield create_client


async def test_create_client_returns_emcache_client(memcached_container, guillotina_main, loop):
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
    "param,value",
    [
        ("timeout", 1.0),
        ("max_connections", 20),
        ("purge_unused_connections_after", 1),
        ("connection_timeout", 20),
        ("purge_unhealthy_nodes", True),
    ],
)
async def test_create_client_sets_configured_params(mocked_create_client, param, value):
    settings = {"hosts": MOCK_HOSTS}
    driver = MemcachedDriver()
    await driver._create_client({**settings, **{param: value}})
    assert mocked_create_client.call_args[1][param] == value


@pytest.mark.app_settings(MEMCACHED_SETTINGS)
async def test_memcached_ops(memcached_container, guillotina_main, loop):
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
async def test_memcached_ops_are_safe_key(memcached_container, guillotina_main, loop, unsafe_key):
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
