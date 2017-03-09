from guillotina.async import IQueueUtility
from guillotina.component import getUtility
from guillotina.interfaces import IApplication
from guillotina.testing import AsyncMockView
from guillotina.tests import utils


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

    app.del_async_utility(QUEUE_UTILITY_CONFIG)
