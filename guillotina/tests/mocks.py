from guillotina.db.interfaces import IStorage
from zope.interface import implementer


class MockDBTransaction:
    '''
    a db transaction is different than a transaction from guillotina
    '''

    def __init__(self, storage, trns):
        self._storage = storage
        self._transaciont = trns


@implementer(IStorage)
class MockStorage:

    _cache = {}
    _read_only = False
    _transaction_strategy = 'merge'

    def __init__(self):
        self._transaction = None

    async def get_annotation(self, trns, oid, id):
        return None

    async def start_transaction(self, trns):
        self._transaction = MockDBTransaction(self, trns)
        return self._transaction

    async def get_next_tid(self, trns):
        return 1


class MockTransactionManager:
    _storage = None

    def __init__(self):
        self._storage = MockStorage()
