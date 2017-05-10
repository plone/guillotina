from collections import OrderedDict
from guillotina.component import getMultiAdapter
from guillotina.component import queryMultiAdapter
from guillotina.db.interfaces import IConflictResolver
from guillotina.db.interfaces import IStorageCache
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionStrategy
from guillotina.db.interfaces import IWriter
from guillotina.db.reader import reader
from guillotina.exceptions import ConflictError
from guillotina.exceptions import ReadOnlyError
from guillotina.exceptions import RequestNotFound
from guillotina.exceptions import Unauthorized
from guillotina.exceptions import UnresolvableConflict
from guillotina.utils import get_current_request
from zope.interface import implementer

import asyncio
import logging
import sys
import time
import uuid


HARD_CACHE = {}


logger = logging.getLogger(__name__)


class Status:
    # ACTIVE is the initial state.
    ACTIVE = "Active"
    COMMITTING = "Committing"
    COMMITTED = "Committed"
    ABORTED = "Aborted"


@implementer(ITransaction)
class Transaction(object):

    def __init__(self, manager, request=None, loop=None):
        self._txn_time = None
        self._tid = None
        self.status = Status.ACTIVE

        # Transaction Manager
        self._manager = manager

        # List of objects added
        # needs to be ordered because content inserted after other might
        # reference each other
        self.added = OrderedDict()
        self.modified = {}
        self.deleted = {}

        # OIDS to invalidate
        self._to_invalidate = []

        # List of (hook, args, kws) tuples added by addBeforeCommitHook().
        self._before_commit = []

        # List of (hook, args, kws) tuples added by addAfterCommitHook().
        self._after_commit = []

        logger.debug("new transaction")

        # Connection to DB
        self._db_conn = None
        # Transaction on DB
        self._db_txn = None
        # Lock on the transaction
        # some databases need to lock during queries
        # this provides a lock for each transaction
        # which would correspond with one connection
        self._lock = asyncio.Lock(loop=loop)

        # we *not* follow naming standards of using "_request" here so
        # get_current_request can magically find us here...
        self.request = request
        self._strategy = getMultiAdapter(
            (manager._storage, self), ITransactionStrategy,
            name=manager._storage._transaction_strategy)
        self._cache = manager._storage._cache

    @property
    def strategy(self):
        return self._strategy

    def get_before_commit_hooks(self):
        """ See ITransaction.
        """
        return iter(self._before_commit)

    def add_before_commit_hook(self, hook, args=(), kws=None):
        """ See ITransaction.
        """
        if kws is None:
            kws = {}
        self._before_commit.append((hook, tuple(args), kws))

    def get_after_commit_hooks(self):
        """ See ITransaction.
        """
        return iter(self._after_commit)

    def add_after_commit_hook(self, hook, args=(), kws=None):
        """ See ITransaction.
        """
        if kws is None:
            kws = {}
        self._after_commit.append((hook, tuple(args), kws))

    async def _call_after_commit_hooks(self, status=True):
        # Avoid to abort anything at the end if no hooks are registred.
        if not self._after_commit:
            return
        # Call all hooks registered, allowing further registrations
        # during processing.  Note that calls to addAterCommitHook() may
        # add additional hooks while hooks are running, and iterating over a
        # growing list is well-defined in Python.
        for hook, args, kws in self._after_commit:
            # The first argument passed to the hook is a Boolean value,
            # true if the commit succeeded, or false if the commit aborted.
            try:
                await hook(status, *args, **kws)
            except:  # noqa
                # We need to catch the exceptions if we want all hooks
                # to be called
                logger.error("Error in after commit hook exec in %s ",
                             hook, exc_info=sys.exc_info())
        self._after_commit = []
        self._before_commit = []

    # BEGIN TXN

    async def tpc_begin(self, conn):
        """Begin commit of a transaction

        conn is a real db that will be got by db.open()
        """
        self._txn_time = time.time()
        self._db_conn = conn
        await self._strategy.tpc_begin()

    def check_read_only(self):
        if self.request is None:
            try:
                self.request = get_current_request()
            except RequestNotFound:
                return False
        if hasattr(self.request, '_db_write_enabled') and not self.request._db_write_enabled:
            raise Unauthorized('Adding content not permited')
        # Add the new tid
        if self._manager._storage._read_only:
            raise ReadOnlyError()

    # REGISTER OBJECTS

    def register(self, obj, new_oid=None):
        """We are adding a new object on the DB"""
        self.check_read_only()

        if obj._p_jar is None:
            obj._p_jar = self

        oid = obj._p_oid
        new = False
        if oid is None:
            if new_oid is not None:
                new = True
            else:
                new_oid = uuid.uuid4().hex
            oid = new_oid

        obj._p_oid = oid
        if new or obj.__new_marker__:
            self.added[oid] = obj
            obj.__new_marker__ = False
        elif oid not in self.modified:
            self.modified[oid] = obj

    def delete(self, obj):
        self.check_read_only()
        oid = obj._p_oid
        if oid is not None:
            if oid in self.modified:
                del self.modified[oid]
            elif oid in self.added:
                del self.added[oid]
            self.deleted[oid] = obj

    async def clean_cache(self):
        HARD_CACHE.clear()
        await self._cache.clear()

    # GET AN OBJECT

    async def get(self, oid):
        """Getting a oid from the db"""

        obj = self.modified.get(oid, None)
        if obj is not None:
            return obj

        result = HARD_CACHE.get(oid, None)
        if result is None:
            result = await self._cache.get(oid, None)

        if result is not None:
            obj = reader(result)
            obj._p_jar = self
            return obj

        result = await self._manager._storage.load(self, oid)
        obj = reader(result)
        obj._p_jar = self

        if obj.__cache__ == 0:
            HARD_CACHE[oid] = result
        else:
            await self._cache.set(oid, result)

        return obj

    async def commit(self):
        await self._call_before_commit_hooks()
        self.status = Status.COMMITTING
        await self.real_commit()
        await self.tpc_vote()
        await self.tpc_finish()
        self.status = Status.COMMITTED
        await self._call_after_commit_hooks()

    async def abort(self):
        self.status = Status.ABORTED
        await self._manager._storage.abort(self)
        self.tpc_cleanup()

    async def _call_before_commit_hooks(self):
        for hook, args, kws in self._before_commit:
            await hook(*args, **kws)
        self._before_commit = []

    async def _store_object(self, obj, oid, added=False):
        # Modified objects
        if obj._p_jar is not self and obj._p_jar is not None:
            raise Exception('Invalid reference to txn')

        # There is no serial
        if added:
            serial = None
        else:
            serial = getattr(obj, "_p_serial", 0)
        s, l = await self._manager._storage.store(
            oid, serial, IWriter(obj), obj, self)
        obj._p_serial = s
        obj._p_oid = oid
        if obj._p_jar is None:
            obj._p_jar = self
        self._to_invalidate.append(obj)

    async def real_commit(self):
        """Commit changes to an object"""
        for oid, obj in self.added.items():
            await self._store_object(obj, oid, True)
        for oid, obj in self.modified.items():
            await self._store_object(obj, oid)
        for oid, obj in self.deleted.items():
            if obj._p_jar is not self and obj._p_jar is not None:
                raise Exception('Invalid reference to txn')
            await self._manager._storage.delete(self, oid)
            self._to_invalidate.append(obj)

    async def tpc_vote(self):
        """Verify that a data manager can commit the transaction."""
        ok = await self._strategy.tpc_vote()
        if ok is False:
            await self._manager.abort(request=self.request, txn=self)
            raise ConflictError(self)

    async def resolve_conflict(self, conflict):
        if conflict['zoid'] not in self.modified:
            raise Exception('Attempting to resolve conflict on object that is '
                            'not registered with this transaction')

        this_ob = self.modified[conflict['zoid']]
        conflicted_ob = reader(conflict)
        resolver = queryMultiAdapter((this_ob, conflicted_ob), IConflictResolver)
        if resolver is not None:
            resolved_ob = await resolver.resolve()
            if resolved_ob is not None:
                resolved_ob._p_oid = this_ob._p_oid
                resolved_ob._p_jar = self
                self.modified[this_ob._p_oid] = resolved_ob
                return resolved_ob
        raise UnresolvableConflict(this_ob, conflicted_ob)

    async def tpc_finish(self):
        """Indicate confirmation that the transaction is done.
        """
        await self._strategy.tpc_finish()
        self.tpc_cleanup()

    def tpc_cleanup(self):
        self.added = {}
        self.modified = {}
        self.deleted = {}
        for obj in self._to_invalidate:
            obj.__changes__.clear()
            # would also invalidate cache here when it's all said and done...
        self._to_invalidate = []
        self._db_txn = None

    # Inspection

    async def keys(self, oid):
        keys = []
        for record in await self._manager._storage.keys(self, oid):
            keys.append(record['id'])
        return keys

    async def get_child(self, container, key):
        result = await self._cache.get_child(container._p_oid, key)
        if result is None:
            result = await self._manager._storage.get_child(self, container._p_oid, key)
            if result is None:
                return None
            await self._cache.set_child(container._p_oid, key, result)

        obj = reader(result)
        obj.__parent__ = container
        obj._p_jar = self
        return obj

    async def contains(self, oid, key):
        return await self._manager._storage.has_key(self, oid, key)  # noqa

    async def len(self, oid):
        result = await self._cache.get_len(oid)
        if result is None:
            result = await self._manager._storage.len(self, oid)
            await self._cache.set_len(oid, result)
        return result

    async def items(self, container):
        async for record in self._manager._storage.items(self, container._p_oid):
            obj = reader(record)
            obj.__parent__ = container
            obj._p_jar = self
            yield obj.id, obj

    async def get_annotation(self, base_obj, id):
        result = await self._cache.get_child(base_obj._p_oid, id, prefix='annotation')
        if result is None:
            result = await self._manager._storage.get_annotation(self, base_obj._p_oid, id)
            if result is None:
                raise KeyError(id)
            await self._cache.set_child(base_obj._p_oid, id, result, prefix='annotation')
        obj = reader(result)
        obj.__of__ = base_obj._p_oid
        obj._p_jar = self
        return obj

    async def get_annotation_keys(self, oid):
        return [r['id'] for r in await self._manager._storage.get_annotation_keys(self, oid)]

    async def del_blob(self, bid):
        return await self._manager._storage.del_blob(self, bid)

    async def write_blob_chunk(self, bid, oid, chunk_index, data):
        return await self._manager._storage.write_blob_chunk(self, bid, oid, chunk_index, data)

    async def read_blob_chunk(self, bid, chunk=0):
        return await self._manager._storage.read_blob_chunk(self, bid, chunk)

    async def read_blob_chunks(self, bid):
        return await self._manager._storage.read_blob_chunks(self, bid)

    async def get_total_number_of_objects(self):
        return await self._manager._storage.get_total_number_of_objects(self)

    async def get_total_number_of_resources(self):
        return await self._manager._storage.get_total_number_of_resources(self)
