from guillotina.component import getMultiAdapter
from guillotina.db.cache.dummy import DummyCache
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionStrategy
from zope.interface import implementer


class MockDBTransaction:
    '''
    a db transaction is different than a transaction from guillotina
    '''

    def __init__(self, storage, trns):
        self._storage = storage
        self._transacion = trns


@implementer(ITransaction)
class MockTransaction:
    def __init__(self, manager=None):
        if manager is None:
            manager = MockTransactionManager()
        self._manager = manager
        self._tid = 1
        self.modified = {}
        self.request = None
        self._strategy = getMultiAdapter(
            (manager._storage, self), ITransactionStrategy,
            name=manager._storage._transaction_strategy)
        self._cache = DummyCache(manager._storage, self)

    async def refresh(self, ob):
        return ob

    def register(self, ob):
        self.modified[ob._p_oid] = ob

    def tpc_cleanup(self):
        pass


@implementer(IStorage)
class MockStorage:

    _cache = {}
    _read_only = False
    _transaction_strategy = 'resolve'
    _cache_strategy = 'dummy'
    _options = {}

    def __init__(self, transaction_strategy='resolve', cache_strategy='dummy'):
        self._transaction_strategy = transaction_strategy
        self._cache_strategy = cache_strategy
        self._transaction = None

    async def get_annotation(self, trns, oid, id):
        return None

    async def start_transaction(self, trns):
        self._transaction = MockDBTransaction(self, trns)
        return self._transaction

    async def get_next_tid(self, trns):
        return 1

    async def abort(self, txn):
        pass

    async def commit(self, txn):
        pass


class MockTransactionManager:
    _storage = None

    def __init__(self, storage=None):
        if storage is None:
            storage = MockStorage()
        self._storage = storage

    async def _close_txn(self, *args, **kwargs):
        pass
