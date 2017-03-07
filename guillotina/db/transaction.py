from guillotina.db.interfaces import IWriter
from guillotina.db.reader import reader
from guillotina.exceptions import Unauthorized
from guillotina.utils import get_current_request

import logging
import sys
import time
import uuid


def reraise(tp, value, tb=None):  # pragma NO COVER
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value


logger = logging.getLogger(__name__)


class Status:
    # ACTIVE is the initial state.
    ACTIVE = "Active"
    COMMITTING = "Committing"
    COMMITTED = "Committed"
    ABORTED = "Aborted"


class Transaction(object):

    def __init__(self, manager, request=None):
        self._txn_time = None
        self._tid = None
        self.status = Status.ACTIVE

        # Transaction Manager
        self._manager = manager

        # List of objects added
        self.added = []
        self.modified = {}
        self.deleted = {}

        # List of (hook, args, kws) tuples added by addBeforeCommitHook().
        self._before_commit = []

        # List of (hook, args, kws) tuples added by addAfterCommitHook().
        self._after_commit = []

        logger.debug("new transaction")

        # Connection to DB
        self._db_conn = None
        # Transaction on DB
        self._db_txn = None
        self.request = request

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
                hook(status, *args, **kws)
            except:
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
        self._cache = self._manager._storage._cache.copy()
        self._txn_time = time.time()
        await self._manager._storage.tpc_begin(self, conn)

    def check_read_only(self):
        if self.request is None:
            self.request = get_current_request()
        if hasattr(self.request, '_db_write_enabled') and not self.request._db_write_enabled:
            raise Unauthorized('Adding content not permited')

    # REGISTER OBJECTS

    def register(self, obj, new_oid=None):
        """We are adding a new object on the DB"""
        self.check_read_only()

        oid = obj._p_oid
        if oid is None:
            self.added.append(obj)
            if new_oid is None:
                new_oid = uuid.uuid4().hex
            obj._p_oid = new_oid
        else:
            self.modified[oid] = obj

    def delete(self, obj):
        self.check_read_only()
        oid = obj._p_oid
        if oid is not None:
            if oid in self.modified:
                del self.modified[oid]
            self.deleted[oid] = obj

    # GET AN OBJECT

    async def get(self, oid):
        """Getting a oid from the db"""

        obj = self.modified.get(oid, None)
        if obj is not None:
            return obj

        obj = self._cache.get(oid, None)
        if obj is not None:
            return obj

        result = await self._manager._storage.load(self, oid)
        obj = reader(result)
        obj._p_jar = self

        self._cache[oid] = obj

        return obj

    async def get_all(self, oid):
        """Getting a oid from the db"""

        obj = self.modified.get(oid, None)
        if obj is not None:
            return obj
        result = await self._manager._storage.load_all(self, oid)
        obj = reader(result)
        obj._p_jar = self
        return obj

    async def get_annotation(self, oid, annotation_id):
        """Getting a oid from the db"""

        obj = self.modified.get(oid, None)
        if obj is None:
            obj = self._cache.get(oid, None)
        if obj is not None and \
                annotation_id in obj.__annotations__:
            # Its loaded
            return obj.__annotations__[annotation_id]
        result = await self._manager._storage.get_annotation(
            self, oid, annotation_id)
        obj = reader(result)
        obj._p_jar = self
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

    async def real_commit(self):
        """Commit changes to an object"""
        await self._manager._storage.precommit(self)
        for obj in self.added:
            # Added objects
            if obj._p_jar is not self and obj._p_jar is not None:
                raise Exception('Invalid reference to txn')

            # There is no oid
            oid = obj._p_oid
            if oid is None:
                oid = uuid.uuid4().hex
            s, l = await self._manager._storage.store(
                oid, None, IWriter(obj), obj, self)
            obj._p_serial = s
            obj._p_oid = oid
            if obj._p_jar is None:
                obj._p_jar = self
        for oid, obj in self.modified.items():
            # Modified objects
            if obj._p_jar is not self and obj._p_jar is not None:
                raise Exception('Invalid reference to txn')

            # There is no serial
            serial = getattr(obj, "_p_serial", 0)

            s, l = await self._manager._storage.store(
                oid, serial, IWriter(obj), obj, self)
            obj._p_serial = s
            if obj._p_jar is None:
                obj._p_jar = self
        for oid, obj in self.deleted.items():
            if obj._p_jar is not self and obj._p_jar is not None:
                raise Exception('Invalid reference to txn')
            await self._manager._storage.delete(self, oid)

    async def tpc_vote(self):
        """Verify that a data manager can commit the transaction."""
        s = await self._manager._storage.tpc_vote(self)
        if s is False:
            raise Exception('Conflict Error')

    async def tpc_finish(self):
        """Indicate confirmation that the transaction is done.
        """
        await self._manager._storage.tpc_finish(self)
        self.tpc_cleanup()

    def tpc_cleanup(self):
        self.added = []
        self.modified = {}
        self.deleted = {}
        self._db_txn = None

    # Inspection

    async def keys(self, oid):
        return await self._manager._storage.keys(self, oid)

    async def get_child(self, oid, key):
        result = await self._manager._storage.get_child(self, oid, key)
        obj = reader(result)
        obj._p_jar = self
        return obj

    async def contains(self, oid, key):
        return await self._manager._storage.has_key(self, oid, key)

    async def len(self, oid):
        return await self._manager._storage.len(self, oid)

    async def items(self, oid):
        async for record in self._manager._storage.items(self, oid):
            obj = reader(record)
            obj._p_jar = self
            yield obj.id, obj
