from plone.server.testing import PloneQueueServerTestCase
from zope.component import getUtility
from plone.server.async import IQueueUtility
import asyncio
from plone.server.testing import AsyncMockView


class TestQueue(PloneQueueServerTestCase):

    def test_add_sync_utility(self):
        util = getUtility(IQueueUtility)
        var = []

        async def printHi():
            var.append('hola')

        v = AsyncMockView(self.layer.app['plone'], self.layer.app['plone'].conn, printHi)
        loop = asyncio.get_event_loop()
        future = asyncio.run_coroutine_threadsafe(util.add(v), loop)
        future2 = asyncio.run_coroutine_threadsafe(util.add(v), loop)
        total = future.result()
        total = future2.result()

        future = asyncio.run_coroutine_threadsafe(util._queue.join(), loop)
        total = future.result()
        self.assertTrue('hola' in var)
        self.assertTrue(len(var) == 2)
