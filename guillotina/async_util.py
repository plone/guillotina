from datetime import datetime
from dateutil.tz import tzutc
from guillotina import configure
from guillotina import logger
from guillotina.browser import ErrorResponse
from guillotina.browser import UnauthorizedResponse
from guillotina.browser import View
from guillotina.db.transaction import Status
from guillotina.exceptions import ServerClosingException
from guillotina.exceptions import Unauthorized
from guillotina.interfaces import IAsyncJobPool
from guillotina.interfaces import IAsyncUtility  # noqa
from guillotina.interfaces import IQueueUtility  # noqa
from guillotina.transactions import get_tm
from guillotina.transactions import get_transaction
from guillotina.transactions import managed_transaction

import aiotask_context
import asyncio
import typing


_zone = tzutc()


class QueueUtility(object):

    def __init__(self, settings, loop=None):
        self._queue = asyncio.Queue(loop=loop)
        self._exceptions = False
        self._total_queued = 0

    async def initialize(self, app=None):
        # loop
        self.app = app
        while True:
            got_obj = False
            try:
                view = await self._queue.get()
                got_obj = True
                txn = get_transaction(view.request)
                tm = get_tm(view.request)
                if txn is None or (txn.status in (
                        Status.ABORTED, Status.COMMITTED, Status.CONFLICT) and
                        txn._db_conn is None):
                    txn = await tm.begin(view.request)
                else:
                    # still finishing current transaction, this connection
                    # will be cut off, so we need to wait until we no longer
                    # have an active transaction on the reqeust...
                    await self.add(view)
                    await asyncio.sleep(1)
                    continue

                try:
                    aiotask_context.set('request', view.request)
                    view_result = await view()
                    if isinstance(view_result, ErrorResponse):
                        await tm.commit(txn=txn)
                    elif isinstance(view_result, UnauthorizedResponse):
                        await tm.abort(txn=txn)
                    else:
                        await tm.commit(txn=txn)
                except Unauthorized:
                    await tm.abort(txn=txn)
                except Exception as e:
                    logger.error(
                        "Exception on writing execution",
                        exc_info=e)
                    await tm.abort(txn=txn)
            except (RuntimeError, SystemExit, GeneratorExit, KeyboardInterrupt,
                    asyncio.CancelledError, KeyboardInterrupt):
                # dive, these errors mean we're exit(ing)
                self._exceptions = True
                return
            except Exception as e:  # noqa
                self._exceptions = True
                logger.error('Worker call failed', exc_info=e)
            finally:
                try:
                    aiotask_context.set('request', None)
                except RuntimeError:
                    pass
                if got_obj:
                    try:
                        view.request.execute_futures()
                    except AttributeError:
                        pass
                    self._queue.task_done()

    @property
    def exceptions(self):
        return self._exceptions

    @property
    def total_queued(self):
        return self._total_queued

    async def add(self, view):
        await self._queue.put(view)
        self._total_queued += 1
        return self._queue.qsize()

    async def finalize(self, app):
        pass


class QueueObject(View):

    def __init__(self, context, request):
        # not sure if we need proxy object here...
        # super(QueueObject, self).__init__(context, TransactionProxy(request))
        super(QueueObject, self).__init__(context, request)
        self.time = datetime.now(tz=_zone).timestamp()

    def __lt__(self, view):
        return self.time < view.time


class Job:

    def __init__(self, func: typing.Callable[[], typing.Coroutine],
                 request=None, args=None, kwargs=None):
        self._func = func
        self._request = request
        self._args = args
        self._kwargs = kwargs

    @property
    def func(self):
        return self._func

    async def run(self):
        try:
            if self._request:
                aiotask_context.set('request', self._request)
                async with managed_transaction(
                        request=self._request, abort_when_done=True):
                    await self._func(*self._args or [], **self._kwargs or {})
            else:
                # if no request, we do it without transaction
                await self._func(*self._args or [], **self._kwargs or {})
        finally:
            aiotask_context.set('request', None)


@configure.utility(provides=IAsyncJobPool)
class AsyncJobPool:

    def __init__(self, max_size=5):
        self._loop = None
        self._running = []
        self._pending = []
        self._max_size = max_size
        self._closing = False

    def get_loop(self):
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        return self._loop

    @property
    def num_pending(self):
        return len(self._pending)

    @property
    def num_running(self):
        return len(self._running)

    async def initialize(self, app=None):
        pass

    async def finalize(self):
        await self.join()

    def add_job(self, func: typing.Callable[[], typing.Coroutine],
                request=None, args=None, kwargs=None):
        if self._closing:
            raise ServerClosingException('Can not schedule job')
        job = Job(func, request=request, args=args, kwargs=kwargs)
        self._pending.insert(0, job)
        self._schedule()
        return job

    def _add_job_after_commit(self, status, func, request=None, args=None, kwargs=None):
        self.add_job(func, request=request, args=args, kwargs=kwargs)

    def add_job_after_commit(self, func: typing.Callable[[], typing.Coroutine],
                             request=None, args=None, kwargs=None):
        txn = get_transaction(request)
        txn.add_after_commit_hook(
            self._add_job_after_commit,
            args=[func],
            kws={
                'request': request,
                'args': args,
                'kwargs': kwargs
            })

    def _done_callback(self, task):
        self._running.remove(task)
        self._schedule()  # see if we can schedule now

    def _schedule(self):
        '''
        check if we can schedule a new job
        '''
        if len(self._running) < self._max_size and len(self._pending) > 0:
            job = self._pending.pop()
            task = self.get_loop().create_task(job.run())
            task._job = job
            self._running.append(task)
            task.add_done_callback(self._done_callback)

    async def join(self):
        self._closing = True
        while len(self._running) > 0 or len(self._pending) > 0:
            await asyncio.sleep(0.1)
