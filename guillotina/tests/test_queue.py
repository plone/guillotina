from guillotina.async import IQueueUtility
from guillotina.testing import AsyncMockView
from zope.component import getUtility
from guillotina.tests import utils


async def test_add_sync_utility(guillotina):
    requester = await guillotina

    util = getUtility(IQueueUtility)
    var = []

    async def printHi():
        var.append('hola')

    request = utils.get_mocked_request(requester.db)
    root = await utils.get_root(request)

    view = AsyncMockView(root, request, printHi)
    await util.add(view)
    await util.add(view)
    await util._queue.join()
    assert 'hola' in var
    assert len(var) == 2
