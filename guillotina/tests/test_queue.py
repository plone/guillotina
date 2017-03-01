from guillotina.async import IQueueUtility
from guillotina.testing import AsyncMockView
from guillotina.testing import GuillotinaQueueServerTestCase
from zope.component import getUtility

import asyncio


class TestQueue(GuillotinaQueueServerTestCase):

    def test_add_sync_utility(self):
        util = getUtility(IQueueUtility)
        var = []

        async def printHi():
            var.append('hola')

        context = self.layer.app['guillotina'].conn.root()
        v = AsyncMockView(context, self.layer.app['guillotina'].conn, printHi, self.layer.app)
        loop = asyncio.get_event_loop()
        future = asyncio.run_coroutine_threadsafe(util.add(v), loop)
        future2 = asyncio.run_coroutine_threadsafe(util.add(v), loop)
        total = future.result()
        total = future2.result()

        future = asyncio.run_coroutine_threadsafe(util._queue.join(), loop)
        total = future.result()  # noqa
        self.assertTrue('hola' in var)
        self.assertTrue(len(var) == 2)
