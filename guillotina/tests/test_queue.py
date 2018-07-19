from guillotina.async_util import IAsyncJobPool
from guillotina.async_util import IQueueUtility
from guillotina.browser import View
from guillotina.component import get_utility
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


async def test_add_sync_utility(guillotina, loop):

    util = get_utility(IQueueUtility)
    var = []

    async def printHi(msg):
        await asyncio.sleep(0.01)
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


class JobRunner:

    def __init__(self):
        self.done = False
        self.wait = True

    async def __call__(self, arg1):
        while self.wait:
            await asyncio.sleep(0.05)
        self.done = True


async def test_run_jobs(guillotina):
    pool = get_utility(IAsyncJobPool)
    job = pool.add_job(JobRunner(), args=['foobar'])
    assert pool.num_running == 1
    assert pool.num_pending == 0
    await asyncio.sleep(0.1)
    assert pool.num_running == 1
    job.func.wait = False
    await asyncio.sleep(0.1)
    assert pool.num_running == 0
    assert pool.num_pending == 0
    assert job.func.done


async def test_run_many_jobs(guillotina, dummy_request):
    pool = get_utility(IAsyncJobPool)
    jobs = [pool.add_job(JobRunner(), args=['foobar'], request=dummy_request)
            for _ in range(20)]
    assert pool.num_running == 5
    assert pool.num_pending == 15

    for job in jobs:
        job.func.wait = False

    await asyncio.sleep(0.1)
    assert pool.num_running == 0
    assert pool.num_pending == 0

    for job in jobs:
        assert job.func.done
