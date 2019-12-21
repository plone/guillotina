from dateutil.tz import tzutc
from guillotina import logger
from guillotina import task_vars
from guillotina.db.transaction import Status
from guillotina.exceptions import ServerClosingException
from guillotina.exceptions import TransactionNotFound
from guillotina.interfaces import IAsyncJobPool  # noqa
from guillotina.interfaces import IAsyncUtility  # noqa
from guillotina.interfaces import IQueueUtility  # noqa
from guillotina.transactions import get_tm
from guillotina.transactions import get_transaction
from guillotina.transactions import transaction
from guillotina.utils import dump_task_vars
from guillotina.utils import execute
from guillotina.utils import load_task_vars

import asyncio
import typing


_zone = tzutc()


class QueueUtility(object):
    def __init__(self, settings=None, loop=None):
        self._queue = None
        self._loop = loop
        self._exceptions = False
        self._total_queued = 0

    @property
    def queue(self):
        if self._queue is None:
            self._queue = asyncio.Queue(loop=self._loop)
        return self._queue

    async def initialize(self, app=None):
        # loop
        self.app = app
        while True:
            got_obj = False
            try:
                func, tvars = await self.queue.get()
                got_obj = True
                load_task_vars(tvars)
                txn = get_transaction()
                tm = get_tm()
                if txn is None or (
                    txn.status in (Status.ABORTED, Status.COMMITTED, Status.CONFLICT) and txn._db_conn is None
                ):
                    txn = await tm.begin()
                else:
                    # still finishing current transaction, this connection
                    # will be cut off, so we need to wait until we no longer
                    # have an active transaction on the reqeust...
                    await self.queue.put((func, tvars))
                    await asyncio.sleep(0.1)
                    continue

                try:
                    await func()
                    await tm.commit(txn=txn)
                except Exception as e:
                    logger.error("Exception on writing execution", exc_info=e)
                    await tm.abort(txn=txn)
            except (
                RuntimeError,
                SystemExit,
                GeneratorExit,
                KeyboardInterrupt,
                asyncio.CancelledError,
                KeyboardInterrupt,
            ):
                # dive, these errors mean we're exit(ing)
                self._exceptions = True
                return
            except Exception as e:  # noqa
                self._exceptions = True
                logger.error("Worker call failed", exc_info=e)
                execute.clear_futures()
            finally:
                if got_obj:
                    execute.execute_futures()
                    self.queue.task_done()

    @property
    def exceptions(self):
        return self._exceptions

    @property
    def total_queued(self):
        return self._total_queued

    async def add(self, view):
        await self.queue.put((view, dump_task_vars()))
        self._total_queued += 1
        return self.queue.qsize()

    async def finalize(self, app):
        pass


class Job:
    def __init__(
        self, func: typing.Callable[[], typing.Coroutine], _task_vars=None, args=None, kwargs=None
    ) -> None:
        self._func = func
        self._task_vars = _task_vars
        self._args = args
        self._kwargs = kwargs

    @property
    def func(self):
        return self._func

    async def run(self):
        if self._task_vars is not None:
            load_task_vars(self._task_vars)
        tm = task_vars.tm.get()
        if tm is not None:
            async with transaction(tm=tm):
                await self._func(*self._args or [], **self._kwargs or {})
        else:
            # if no request, we do it without transaction
            await self._func(*self._args or [], **self._kwargs or {})


class AsyncJobPool:
    def __init__(self, settings=None, loop=None):
        settings = settings or {"max_size": 5}
        self._loop = None
        self._running = []
        self._pending = []
        self._max_size = settings["max_size"]
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

    def add_job(self, func: typing.Callable[[], typing.Coroutine], args=None, kwargs=None):
        if self._closing:
            raise ServerClosingException("Can not schedule job")
        job = Job(func, _task_vars=dump_task_vars(), args=args, kwargs=kwargs)
        self._pending.insert(0, job)
        self._schedule()
        return job

    def _add_job_after_commit(self, status, func, args=None, kwargs=None):
        self.add_job(func, args=args, kwargs=kwargs)

    def add_job_after_commit(self, func: typing.Callable[[], typing.Coroutine], args=None, kwargs=None):
        txn = get_transaction()
        if txn is not None:
            txn.add_after_commit_hook(
                self._add_job_after_commit, args=[func], kws={"args": args, "kwargs": kwargs}
            )
        else:
            raise TransactionNotFound("Could not find transaction to run job with")

    def _done_callback(self, task):
        self._running.remove(task)
        self._schedule()  # see if we can schedule now

    def _schedule(self):
        """
        check if we can schedule a new job
        """
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
