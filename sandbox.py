# -*- coding: utf-8 -*-
from BTrees.Length import Length
from aiohttp import web
from aiohttp_traversal.abc import AbstractResource
from aiohttp_traversal.ext.views import View
from aiohttp_traversal import TraversalRouter
from aiohttp_traversal.traversal import traverse, Traverser
from BTrees._OOBTree import OOBTree
from concurrent.futures import ThreadPoolExecutor
from transaction.interfaces import ISavepointDataManager
from zope.interface import implementer
import Acquisition
import ExtensionClass
import logging
import sys
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


@implementer(ISavepointDataManager)
class RequestDataManager(object):

    # noinspection PyProtectedMember
    def __init__(self, request, connection):
        self.request = request
        self.connection = connection
        self._registered_objects = []

    @property
    def txn_manager(self):
        return self.connection.transaction_manager

    def abort(self, txn):
        delattr(self.request, '_txn_dm')
        return self.connection.abort(txn)

    def tpc_begin(self, txn):
        # XXX: ZODB.Connection.Connection instance can only handle a single
        # connection at time and that limit is now only enforced by relying on
        # single thread ThreadPoolExecutor...

        # noinspection PyProtectedMember
        self.connection._registered_objects.extend(self._registered_objects)
        return self.connection.tpc_begin(txn)

    def commit(self, txn):
        return self.connection.commit(txn)

    def tpc_vote(self, txn):
        return self.connection.tpc_vote(txn)

    def tpc_finish(self, txn):
        return self.connection.tpc_finish(txn)

    def tpc_abort(self, txn):
        return self.connection.tpc_abort(txn)

    def sortKey(self):
        return self.connection.sortKey()

    def savepoint(self):
        return self.connection.savepoint()


def get_current_request():
    for i in range(2, 10):  # _request should be found at depth 2
        # noinspection PyProtectedMember
        frame = sys._getframe(i)
        context = frame.f_locals.get('self')
        request = getattr(context, '_request', None)
        if request is not None:
            return request
    raise RuntimeError('Unable to find the current request')


class RequestAwareConnection(ZODB.Connection.Connection):

    def _register(self, obj=None):
        if not hasattr(obj, '_request'):
            return super(RequestAwareConnection, self)._register(obj)

        request = get_current_request()
        if not hasattr(request, '_txn_dm'):
            request._txn_dm = RequestDataManager(request, self)
            self.transaction_manager.get(request).join(request._txn_dm)

        if obj is not None:
            # noinspection PyProtectedMember
            request._txn_dm._registered_objects.append(obj)


class RequestAwareDB(ZODB.DB):
    klass = RequestAwareConnection


class RequestContainer(ExtensionClass.Base):

    def __init__(self, request):
        self._request = request


class RequestAware(Acquisition.Explicit):
    _request = Acquisition.Acquired


class Counter(Length, RequestAware):
    pass


class Container(OOBTree, RequestAware):
    async def __getchild__(self, name):
        container = Acquisition.aq_base(self)
        if name not in container:
            container[name] = Container()
            container[name]['__name__'] = name
            container[name]['__visited__'] = Counter()
        return container[name].__of__(self)


# DB = RequestAwareDB(None)  # volatile
DB = RequestAwareDB('Data.fs')

# Initialize
conn = DB.open(transaction_manager=transaction.manager)
if getattr(conn.root, 'data', None) is None:
    with transaction.manager:
        conn.root.data = Container()
        conn.root._p_changed = 1
conn.close()

TM = RequestAwareTransactionManager()
CONNECTION = DB.open(transaction_manager=TM)


class RequestTraversalRouter(TraversalRouter):
    async def traverse(self, request, *args, **kwargs):
        path = list(p for p in request.path.split('/') if p)
        root = self.get_root(request, *args, **kwargs)  # added request
        if path:
            return await traverse(root, path)
        else:
            return root, path


class RootFactory(AbstractResource):

    __parent__ = None

    def __init__(self, request):
        self.app = RequestContainer(request)

    def __getitem__(self, name):
        return Traverser(self, (name,))

    async def __getchild__(self, name):
        global TM, CONNECTION
        return await CONNECTION.root.data.__of__(self.app).__getchild__(name)


class ContainerView(View):
    async def __call__(self):
        counter = Acquisition.aq_base(self.resource)['__visited__']
        counter.__of__(self.resource).change(1)

        parts = [
            str(counter()),
            Acquisition.aq_base(self.resource)['__name__']
        ]
        parent = Acquisition.aq_parent(self.resource)

        while parent is not None and parent.get('__name__') is not None:
            parts.append(Acquisition.aq_base(parent)['__name__'])
            parent = Acquisition.aq_parent(parent)

        await self.request.app.loop.run_in_executor(
                self.request.app.executor,
                TM.get(self.request).commit)

        return web.Response(text='/'.join(reversed(parts)))


def main():
    logging.basicConfig(level=logging.INFO)
    app = web.Application(router=RequestTraversalRouter())
    app.executor = ThreadPoolExecutor(max_workers=1)
    app.router.set_root_factory(RootFactory)
    app.router.bind_view(Container, ContainerView)
    web.run_app(app)
    logger.info('HTTP server running at http://localhost:8080/')


if __name__ == "__main__":
    main()
