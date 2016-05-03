# -*- coding: utf-8 -*-
from aiohttp import web
from aiohttp.web import RequestHandler
from aiohttp_traversal.abc import AbstractResource
from aiohttp_traversal.ext.views import View
from aiohttp_traversal import TraversalRouter
from aiohttp_traversal.traversal import Traverser
from BTrees.Length import Length
from BTrees._OOBTree import OOBTree
from concurrent.futures import ThreadPoolExecutor
from transaction.interfaces import ISavepointDataManager
from zope.interface import implementer
import asyncio
import inspect
import logging
import transaction
import ZODB
import ZODB.Connection

logger = logging.getLogger('sandbox')


class RequestAwareTransactionManager(transaction.TransactionManager):

    # ITransactionManager
    def begin(self, request=None):
        assert request is not None, \
            'Request aware TM called without request'

        txn = getattr(request, '_txn', None)
        if txn is not None:
            txn.abort()
        txn = request._txn = transaction.Transaction(self._synchs, self)

        # ISynchronizer
        if self._synchs:
            self._synchs.map(lambda s: s.newTransaction(txn))

        return txn

    # ITransactionManager
    def get(self, request=None):
        assert request is not None, \
            'Request aware TM called without request'

        if getattr(request, '_txn', None) is None:
            request._txn = transaction.Transaction(self._synchs, self)
        return request._txn

    # ITransactionManager
    def free(self, txn):
        pass


# noinspection PyProtectedMember
@implementer(ISavepointDataManager)
class RequestDataManager(object):

    def __init__(self, request, connection):
        self.request = request
        self.connection = connection
        self._registered_objects = []
        self._savepoint_storage = None

    @property
    def txn_manager(self):
        return self.connection.transaction_manager

    def abort(self, txn):
        self.connection._registered_objects = self._registered_objects
        self.connection._savepoint_storage = self._savepoint_storage
        self.connection.abort(txn)
        self._registered_objects = []
        self._savepoint_storage = None
        delattr(self.request, '_txn_dm')

    def tpc_begin(self, txn):
        self.connection._registered_objects = self._registered_objects
        self.connection._savepoint_storage = self._savepoint_storage
        return self.connection.tpc_begin(txn)

    def commit(self, txn):
        self.connection.commit(txn)

    def tpc_vote(self, txn):
        self.connection.tpc_vote(txn)

    def tpc_finish(self, txn):
        self.connection.tpc_finish(txn)
        self._registered_objects = []
        self._savepoint_storage = None

    def tpc_abort(self, txn):
        self.connection.tpc_abort(txn)
        self._registered_objects = []
        self._savepoint_storage = None

    def sortKey(self):
        return self.connection.sortKey()

    def savepoint(self):
        self.connection._registered_objects = self._registered_objects
        self.connection._savepoint_storage = self._savepoint_storage
        savepoint = self.connection.savepoint()
        self._registered_objects = []
        self._savepoint_storage = None
        return savepoint


def get_current_request():
    """Get the nearest request from the current frame stack"""
    frame = inspect.currentframe()
    while frame is not None:
        if isinstance(frame.f_locals.get('self'), View):
            return frame.f_locals.get('self').request
        elif isinstance(frame.f_locals.get('self'), RequestHandler):
            return frame.f_locals['request']
        frame = frame.f_back
    raise RuntimeError('Unable to find the current request')


# noinspection PyProtectedMember
class RequestAwareConnection(ZODB.Connection.Connection):
    def _register(self, obj=None):
        request = get_current_request()
        if not hasattr(request, '_txn_dm'):
            request._txn_dm = RequestDataManager(request, self)
            self.transaction_manager.get(request).join(request._txn_dm)

        if obj is not None:
            request._txn_dm._registered_objects.append(obj)


class RequestAwareDB(ZODB.DB):
    klass = RequestAwareConnection


# noinspection PyProtectedMember
class Container(OOBTree):
    @property
    def __parent__(self):
        return getattr(self, '_v_parent', None)

    async def __getchild__(self, name):
        if name not in self:
            self[name] = Container()
            self[name]['__name__'] = name
            self[name]['__visited__'] = Length()
        self[name]._v_parent = self
        return self[name]


# Initialize DB
DB = ZODB.DB('Data.fs')
CONNECTION = DB.open()
if getattr(CONNECTION.root, 'data', None) is None:
    with transaction.manager:
        CONNECTION.root.data = Container()
        CONNECTION.root._p_changed = 1
CONNECTION.close()
DB.close()


# Set request aware classes for app
DB = RequestAwareDB('Data.fs')
TM = RequestAwareTransactionManager()
CONNECTION = DB.open(transaction_manager=TM)


class RootFactory(AbstractResource):

    __parent__ = None

    def __init__(self, app):
        self.app = app

    def __getitem__(self, name):
        return Traverser(self, (name,))

    async def __getchild__(self, name):
        global TM, CONNECTION
        return await CONNECTION.root.data.__getchild__(name)


# noinspection PyProtectedMember
def locked(obj):
    if not hasattr(obj, '_v_lock'):
        obj._v_lock = asyncio.Lock()
    return obj._v_lock


def sync(request):
    return lambda *args, **kwargs: request.app.loop.run_in_executor(
            request.app.executor, *args, **kwargs)


class ContainerView(View):
    async def __call__(self):
        counter = self.resource['__visited__']

        async with locked(counter):
            counter.change(1)
            await sync(self.request)(TM.get(self.request).commit)

        parts = [str(counter()),
                 self.resource['__name__']]
        parent = self.resource.__parent__

        while parent is not None and parent.get('__name__') is not None:
            parts.append(parent['__name__'])
            parent = parent.__parent__

        return web.Response(text='/'.join(reversed(parts)))


def main():
    logging.basicConfig(level=logging.DEBUG)
    app = web.Application(router=TraversalRouter())
    app.executor = ThreadPoolExecutor(max_workers=1)
    app.router.set_root_factory(RootFactory)
    app.router.bind_view(Container, ContainerView)
    web.run_app(app)
    logger.info('HTTP server running at http://localhost:8080/')


if __name__ == "__main__":
    main()
