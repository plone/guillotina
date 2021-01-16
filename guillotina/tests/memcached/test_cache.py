from guillotina.component import get_utility
from guillotina.contrib.memcached.driver import MemcachedDriver
from guillotina.interfaces import ICacheUtility

import pytest


MEMCACHED_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.memcached", "guillotina.contrib.cache"],
    "cache": {"updates_channel": None, "driver": "guillotina.contrib.memcached"},
}


@pytest.mark.app_settings(MEMCACHED_SETTINGS)
async def test_cache_uses_memcached_driver_when_configured(memcached_container, guillotina_main, loop):
    cache = get_utility(ICacheUtility)
    assert isinstance(cache._obj_driver, MemcachedDriver)
    assert cache._obj_driver.initialized is True
