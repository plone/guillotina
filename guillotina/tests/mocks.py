from collections import OrderedDict
from guillotina import app_settings
from guillotina import task_vars
from guillotina.component import query_adapter
from guillotina.db.cache.dummy import DummyCache
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionStrategy
from guillotina.db.interfaces import IWriter
from zope.interface import implementer

import asyncio
import uuid


class MockDBTransaction:
    """
    a db transaction is different than a transaction from guillotina
    """

    def __init__(self, storage, trns):
        self._storage = storage
        self._transacion = trns


@implementer(ITransaction)
class MockTransaction:  # type: ignore
    def __init__(self, manager=None):
        if manager is None:
            manager = MockTransactionManager()
        self._manager = self.manager = manager
        self._tid = 1
        self.modified = OrderedDict()
        self.added = OrderedDict()
        self.deleted = OrderedDict()
        self.request = None
        self._strategy = query_adapter(
            self, ITransactionStrategy, name=manager._storage._transaction_strategy
        )
        self._cache = DummyCache(self)
        self._lock = asyncio.Lock()
        self._status = "started"
        self._db_conn = None
        self.storage = MockStorage()

    async def get_connection(self):
        return self._db_conn

    async def refresh(self, ob):
        return ob

    def register(self, ob, new_oid=None):
        oid = new_oid or ob.__uuid__
        if oid is None:
            oid = app_settings["uid_generator"](ob)
        ob.__uuid__ = oid
        if ob.__new_marker__:
            self.added[oid] = ob
        else:
            self.modified[oid] = ob

    def delete(self, ob):
        self.deleted[ob.__uuid__] = ob

    def tpc_cleanup(self):  # pragma: no cover
        pass

    async def del_blob(self, bid):  # pragma: no cover
        pass

    async def write_blob_chunk(self, bid, zoid, chunk_number, data):  # pragma: no cover
        pass

    async def get_annotation(self, ob, key, reader=None):  # pragma: no cover
        pass

    def __enter__(self):
        task_vars.txn.set(self)
        return self

    def __exit__(self, *args):
        """
        """


@implementer(IStorage)
class MockStorage:  # type: ignore

    _cache: dict = {}
    _read_only = False
    _transaction_strategy = "resolve"
    _options: dict = {}
    supports_unique_constraints = False

    def __init__(self, transaction_strategy="resolve"):
        self._transaction_strategy = transaction_strategy
        self._transaction = None
        self._objects = {}
        self._parent_objs = {}
        self._hits = 0
        self._misses = 0
        self._stored = 0
        self._objects_table_name = "objects"

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

    async def get_child(self, txn, container_uid, key):
        if container_uid not in self._objects:
            return
        children = self._objects[container_uid]["children"]
        if key in children:
            oid = children[key]
            if oid in self._objects:
                return self._objects[oid]

    def store(self, oid, old_serial, writer, ob, txn):
        writer = IWriter(ob)
        self._objects[ob.__uuid__] = {
            "state": writer.serialize(),
            "zoid": ob.__uuid__,
            "tid": 1,
            "id": writer.id,
            "children": self._objects.get(ob.__uuid__, {}).get("children", {}),
        }
        if ob.__parent__ and ob.__parent__.__uuid__ in self._objects:
            self._objects[ob.__parent__.__uuid__]["children"][ob.id] = ob.__uuid__


class MockTransactionManager:  # type: ignore
    _storage = None
    db_id = "root"

    def __init__(self, storage=None):
        if storage is None:
            storage = MockStorage()
        self._storage = storage
        self._hard_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_stored = 0

    async def _close_txn(self, *args, **kwargs):
        pass

    def get(self):
        return task_vars.tm.get()

    async def begin(self):
        txn = MockTransaction(self)
        task_vars.txn.set(txn)
        return txn

    def __enter__(self):
        task_vars.tm.set(self)

    def __exit__(self, *args):
        """
        """


class FakeConnection:
    def __init__(self):
        self.containments = {}
        self.refs = {}
        self.storage = MockStorage()

    async def contains(self, oid, key):
        oids = self.containments[oid]
        return key in [self.refs[oid].id for oid in oids]

    def register(self, ob):
        ob.__txn__ = self
        ob.__uuid__ = uuid.uuid4().hex
        self.refs[ob.__uuid__] = ob
        self.containments[ob.__uuid__] = []
