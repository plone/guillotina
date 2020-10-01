from asyncio import get_running_loop
from guillotina.contrib.memcached.driver import MemcachedDriver
from typing import Any
from typing import Dict


_driver = None

app_settings: Dict[str, Any] = {"memcached": {"hosts": [], "timeout": None, "max_connections": None}}


def includeme(root, settings):
    global _driver
    _driver = MemcachedDriver()


async def get_driver():
    global _driver
    if _driver is None:
        raise Exception("Not added guillotina.contrib.memcached on applications")
    else:
        if _driver.initialized is False:
            loop = get_running_loop()
            await _driver.initialize(loop)
        return _driver
