from datetime import datetime
from dateutil.tz import tzutc
from guillotina import logger
from guillotina.browser import ErrorResponse
from guillotina.browser import UnauthorizedResponse
from guillotina.browser import View
from guillotina.db.transaction import Status
from guillotina.exceptions import Unauthorized
from guillotina.transactions import get_tm
from guillotina.transactions import get_transaction
from zope.interface import Interface

import aiotask_context
import asyncio


_zone = tzutc()


class IAsyncUtility(Interface):

    async def initialize(self):
        '''
        Method that is called on startup and used to create task.
        '''

    async def finalize(self):
        '''
        Called to shut down and cleanup the task
        '''


class IQueueUtility(IAsyncUtility):
    pass


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
