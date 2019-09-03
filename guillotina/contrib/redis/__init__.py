from asyncio import get_running_loop
from guillotina import configure
from guillotina.contrib.redis.driver import RedisDriver


_driver = None

app_settings = {
    "redis": {
        "host": "localhost",
        "port": 6379,
        "pool": {"minsize": 5, "maxsize": 100},
        "cluster_mode": False,
    }
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.redis.dm")
    global _driver
    _driver = RedisDriver()


async def get_driver():
    global _driver
    if _driver is None:
        raise Exception("Not added guillotina.contrib.redis on applications")
    else:
        if _driver.initialized is False:
            loop = get_running_loop()
            await _driver.initialize(loop)
        return _driver
