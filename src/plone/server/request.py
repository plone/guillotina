# -*- coding: utf-8 -*-
import ZODB
import ZODB.Connection

from .utils import get_current_request, sync

import transaction

from transaction.interfaces import ISavepointDataManager

from zope.interface import implementer


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

    def sortKey(self): # noqa
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
        if not hasattr(request, '_txn_dm'):
            request._txn_dm = RequestDataManager(request, self)
            self.transaction_manager.get(request).join(request._txn_dm)

        if obj is not None:
            request._txn_dm._registered_objects.append(obj)


class RequestAwareDB(ZODB.DB):
    klass = RequestAwareConnection
