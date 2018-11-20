from guillotina.component import get_adapter
from guillotina.db.cache.dummy import DummyCache
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionStrategy
from guillotina.db.interfaces import IWriter
from zope.interface import implementer

import asyncio
import uuid


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
        self._manager = self.manager = manager
        self._tid = 1
        self.modified = {}
        self.request = None
        self._strategy = get_adapter(
            self, ITransactionStrategy,
            name=manager._storage._transaction_strategy)
        self._cache = DummyCache(self)
        self._lock = asyncio.Lock()
        self._status = 'started'
        self._db_conn = None

    async def get_connection(self):
        return self._db_conn

    async def refresh(self, ob):
        return ob

    def register(self, ob):
        self.modified[ob._p_oid] = ob

    def tpc_cleanup(self):
        pass

    async def del_blob(self, bid):
        pass

    async def write_blob_chunk(self, bid, zoid, chunk_number, data):
        pass

    async def get_annotation(self, ob, key):
        pass


@implementer(IStorage)
class MockStorage:

    _cache: dict = {}
    _read_only = False
    _transaction_strategy = 'resolve'
    _cache_strategy = 'dummy'
    _options: dict = {}
    supports_unique_constraints = False

    def __init__(self, transaction_strategy='resolve', cache_strategy='dummy'):
        self._transaction_strategy = transaction_strategy
        self._cache_strategy = cache_strategy
        self._transaction = None
        self._objects = {}
        self._parent_objs = {}
        self._hits = 0
        self._misses = 0
        self._stored = 0

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

    async def load(self, txn, oid):
        return self._objects[oid]

    async def get_child(self, txn, container_p_oid, key):
        if container_p_oid not in self._objects:
            return
        children = self._objects[container_p_oid]['children']
        if key in children:
            oid = children[key]
            if oid in self._objects:
                return self._objects[oid]

    def store(self, ob):
        writer = IWriter(ob)
        self._objects[ob._p_oid] = {
            'state': writer.serialize(),
            'zoid': ob._p_oid,
            'tid': 1,
            'id': writer.id,
            'children': self._objects.get(ob._p_oid, {}).get('children', {})
        }
        if ob.__parent__ and ob.__parent__._p_oid in self._objects:
            self._objects[ob.__parent__._p_oid]['children'][ob.id] = ob._p_oid


class MockTransactionManager:
    _storage = None
    db_id = 'root'

    def __init__(self, storage=None):
        if storage is None:
            storage = MockStorage()
        self._storage = storage
        self._hard_cache = {}

    async def _close_txn(self, *args, **kwargs):
        pass

    def get(self, request):
        return request._txn

    async def begin(self, request):
        request._txn = MockTransaction(self)
        return request._txn


class FakeConnection:

    def __init__(self):
        self.containments = {}
        self.refs = {}
        self.storage = MockStorage()

    async def contains(self, oid, key):
        oids = self.containments[oid]
        return key in [self.refs[oid].id for oid in oids]

    def register(self, ob):
        ob._p_jar = self
        ob._p_oid = uuid.uuid4().hex
        self.refs[ob._p_oid] = ob
        self.containments[ob._p_oid] = []
    _p_register = register
