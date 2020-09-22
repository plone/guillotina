from guillotina.utils import resolve_dotted_name

import asyncio
import pytest


@pytest.mark.app_settings({"applications": ["guillotina", "guillotina.contrib.memcached"]})
async def test_memcached_ops(memcached_container, guillotina_main, loop):
    driver = await resolve_dotted_name("guillotina.contrib.memcached").get_driver()
    assert driver.initialized
    assert driver.client is not None

    await driver.set("test", "testdata", expire=10)
    result = await driver.get("test")
    assert result == b"testdata"

    await driver.set("test2", "testdata", expire=10)
    await driver.set("test3", "testdata", expire=10)
    await driver.set("test4", "testdata", expire=1)
    await driver.set("test5", "testdata", expire=20)

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

    await driver.finalize()
    assert driver.initialized is False
