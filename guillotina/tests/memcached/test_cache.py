try:
    from guillotina.contrib.memcached.driver import MemcachedDriver
except ImportError:
    MemcachedDriver = None  # type: ignore
from guillotina.component import get_utility
from guillotina.interfaces import ICacheUtility

import pytest


pytestmark = pytest.mark.asyncio


MEMCACHED_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.memcached", "guillotina.contrib.cache"],
    "cache": {"updates_channel": None, "driver": "guillotina.contrib.memcached"},
}


@pytest.mark.skipif(MemcachedDriver is None, reason="emcache not installed")
@pytest.mark.app_settings(MEMCACHED_SETTINGS)
async def test_cache_uses_memcached_driver_when_configured(memcached_container, guillotina_main):
    cache = get_utility(ICacheUtility)
    assert isinstance(cache._obj_driver, MemcachedDriver)
    assert cache._obj_driver.initialized is True
