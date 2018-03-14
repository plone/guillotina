from guillotina.async_util import IQueueUtility
from guillotina.browser import View
from guillotina.component import get_utility
from guillotina.interfaces import IApplication
from guillotina.tests import utils

import asyncio


class AsyncMockView(View):

    def __init__(self, context, request, func, *args, **kwargs):
        self.context = context
        self.request = request
        self.func = func
        self.args = args
        self.kwargs = kwargs

    async def __call__(self):
        await self.func(*self.args, **self.kwargs)


QUEUE_UTILITY_CONFIG = {
    "provides": "guillotina.async_util.IQueueUtility",
    "factory": "guillotina.async_util.QueueUtility",
    "settings": {}
}


async def test_add_sync_utility(guillotina, loop):
    app = get_utility(IApplication, name='root')
    app.add_async_utility(QUEUE_UTILITY_CONFIG, loop)

    util = get_utility(IQueueUtility)
    var = []

    async def printHi(msg):
        asyncio.sleep(0.01)
        var.append(msg)

    request = utils.get_mocked_request(guillotina.db)
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
