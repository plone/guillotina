# -*- coding: utf-8 -*-
from datetime import datetime
from plone.server.browser import ErrorResponse
from plone.server.browser import UnauthorizedResponse
from plone.server.browser import View
from plone.server import _
from plone.server.transactions import sync
from plone.server.transactions import TransactionProxy
from zope.interface import Interface
from zope.security.interfaces import Unauthorized
import asyncio
import logging

logger = logging.getLogger(__name__)


class IAsyncUtility(Interface):

    async def initialize(self):
        pass


class IQueueUtility(IAsyncUtility):
    pass


class QueueUtility(object):

    def __init__(self, settings):
        self._queue = asyncio.PriorityQueue()
        self._exceptions = False
        self._total_queued = 0

    async def initialize(self, app=None):
        # loop
        self.app = app
        while True:
            got_obj = False
            try:
                priority, view = await self._queue.get()
                request = TransactionProxy(view.request)
                view.request = request
                got_obj = True
                txn = request.conn.transaction_manager.begin(request)
                try:
                    view_result = await view()
                    if isinstance(view_result, ErrorResponse):
                        await sync(request)(txn.abort)
                    elif isinstance(view_result, UnauthorizedResponse):
                        await sync(request)(txn.abort)
                    else:
                        await sync(request)(txn.commit)
                except Unauthorized:
                    await sync(request)(txn.abort)
                    view_result = UnauthorizedResponse(
                        _('Not authorized to render operation'))
                except Exception as e:
                    logger.error(
                        "Exception on writing execution",
                        exc_info=e)
                    await sync(request)(txn.abort)
                    view_result = ErrorResponse(
                        'ServiceError',
                        _('Error on execution of operation')
                    )
            except KeyboardInterrupt or MemoryError or SystemExit or asyncio.CancelledError:
                self._exceptions = True
                raise
            except:
                self._exceptions = True
                logger.error('Worker call failed')
            finally:
                if got_obj:
                    self._queue.task_done()

    @property
    def exceptions(self):
        return self._exceptions

    @property
    def total_queued(self):
        return self._total_queued

    async def add(self, view, priority=3):
        await self._queue.put((priority, view))
        self._total_queued += 1
        return self._queue.qsize()


class QueueObject(View):

    def __init__(self, context, request):
        super(QueueObject, self).__init__(context, request)
        self.time = datetime.now().timestamp()

    def __lt__(self, view):
        return self.time < view.time
