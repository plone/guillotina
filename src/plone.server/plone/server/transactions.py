# -*- coding: utf-8 -*-
from plone.server.utils import get_current_request
from plone.server.utils import sync
from transaction.interfaces import ISavepointDataManager
from zope.interface import implementer

import transaction
import ZODB
import ZODB.Connection


class RequestAwareTransactionManager(transaction.TransactionManager):

    # ITransactionManager
    def begin(self, request=None):
        """Return new request specific transaction
        :param request: current request
        """
        if request is None:
            request = get_current_request()

        txn = getattr(request, '_txn', None)
        if txn is not None:
            txn.abort()
        txn = request._txn = transaction.Transaction(self._synchs, self)

        # ISynchronizer
        if self._synchs:
            self._synchs.map(lambda s: s.newTransaction(txn))

        return txn

    # with
    def __enter__(self):
        raise NotImplementedError()

    def __exit__(self, type_, value, traceback):
        raise NotImplementedError()

    # async with
    async def __aenter__(self):
        return self.begin(get_current_request())

    async def __aexit__(self, type_, value, traceback):
        request = get_current_request()
        if value is None:
            await sync(request)(self.get(request).commit)
        else:
            await sync(request)(self.get(request).abort)

    # ITransactionManager
    def get(self, request=None):
        """Return the current request specific transaction
        :param request: current request
        """
        if request is None:
            request = get_current_request()

        if getattr(request, '_txn', None) is None:
            request._txn = transaction.Transaction(self._synchs, self)
        return request._txn

    # ITransactionManager
    def free(self, txn):
        pass


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
        try:
            delattr(self.request, '_txn_dm')
        except AttributeError:
            # There was no object registered so there is no _txn_dm
            pass

    def tpc_begin(self, txn):
        self.connection._registered_objects = self._registered_objects
        self.connection._savepoint_storage = self._savepoint_storage
        return self.connection.tpc_begin(txn)

    def commit(self, txn):
        self.connection.commit(txn)
        try:
            delattr(self.request, '_txn_dm')
        except AttributeError:
            # There was no object registered so there is no _txn_dm
            pass

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


class RequestAwareConnection(ZODB.Connection.Connection):
    def _register(self, obj=None):
        request = get_current_request()
        if obj._p_jar != self or self != request.conn:
            print(obj._p_jar._db.storage)
            print(self._db.storage)
            print(request.conn._db.storage)
        assert obj._p_jar == self
        assert self == request.conn
        try:
            assert request._txn_dm is not None
        except (AssertionError, AttributeError):
            request._txn_dm = RequestDataManager(request, self)
            self.transaction_manager.get(request).join(request._txn_dm)

        if obj is not None:
            request._txn_dm._registered_objects.append(obj)


class RequestAwareDB(ZODB.DB):
    klass = RequestAwareConnection
