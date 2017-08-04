from guillotina.async import IQueueUtility
from guillotina.component import getUtility
from guillotina.interfaces import IApplication
from guillotina.testing import AsyncMockView
from guillotina.tests import utils

import asyncio


QUEUE_UTILITY_CONFIG = {
    "provides": "guillotina.async.IQueueUtility",
    "factory": "guillotina.async.QueueUtility",
    "settings": {}
}


async def test_add_sync_utility(guillotina, loop):
    requester = await guillotina

    app = getUtility(IApplication, name='root')
    app.add_async_utility(QUEUE_UTILITY_CONFIG, loop)

    util = getUtility(IQueueUtility)
    var = []

    async def printHi(msg):
        asyncio.sleep(0.01)
        var.append(msg)

    request = utils.get_mocked_request(requester.db)
    root = await utils.get_root(request)

    await util.add(AsyncMockView(root, request, printHi, 'hola1'))
    await util.add(AsyncMockView(root, request, printHi, 'hola2'))
    await util.add(AsyncMockView(root, request, printHi, 'hola3'))
    await util.add(AsyncMockView(root, request, printHi, 'hola4'))
    await util._queue.join()
    assert 'hola1' in var
    assert 'hola2' in var
    assert 'hola3' in var
    assert 'hola4' in var
    assert len(var) == 4

    app.del_async_utility(QUEUE_UTILITY_CONFIG)
