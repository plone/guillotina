from collections import OrderedDict
from guillotina._settings import app_settings
from guillotina.component import get_adapter
from guillotina.db.interfaces import IStorageCache
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionStrategy
from guillotina.db.interfaces import IWriter
from guillotina.db.reader import reader
from guillotina.exceptions import ConflictError
from guillotina.exceptions import ReadOnlyError
from guillotina.exceptions import RequestNotFound
from guillotina.exceptions import RestartCommit
from guillotina.exceptions import TIDConflictError
from guillotina.exceptions import Unauthorized
from guillotina.profile import profilable
from guillotina.utils import get_current_request
from guillotina.utils import lazy_apply
from zope.interface import implementer

import asyncio
import logging
import sys
import time


_EMPTY = '__<EMPTY VALUE>__'


logger = logging.getLogger(__name__)


class Status:
    # ACTIVE is the initial state.
    ACTIVE = "Active"
    COMMITTING = "Committing"
    COMMITTED = "Committed"
    ABORTED = "Aborted"
    CONFLICT = 'Conflict'


class cache:

    def __init__(self, key_gen, check_state_size=False):
        self.key_gen = key_gen
        self.check_state_size = check_state_size

    def __call__(self, func):
        this = self

        async def _wrapper(self, *args, **kwargs):
            key_args = this.key_gen(*args, **kwargs)
            result = await self._cache.get(**key_args)
            if result is not None:
                self._cache._hits += 1
                return result
            result = await func(self, *args, **kwargs)

            if result is not None:
                self._cache._misses += 1
                try:
                    if (not this.check_state_size or
                            len(result['state']) < self._cache.max_cache_record_size):
                        await self._cache.set(result, **key_args)
                        self._cache._stored += 1
                except (TypeError, KeyError):
                    await self._cache.set(result, **key_args)
                    self._cache._stored += 1
                return result

        return _wrapper


@implementer(ITransaction)
class Transaction(object):
    _status = 'empty'
    _skip_commit = False

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
        self._objects_to_invalidate = []

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
        self._strategy = get_adapter(self, ITransactionStrategy,
                                     name=manager._storage._transaction_strategy)
        self._cache = get_adapter(self, IStorageCache,
                                  name=manager._storage._cache_strategy)

        self._query_count_start = self._query_count_end = 0

    def get_query_count(self):
        '''
        diff versions of asyncpg
        '''
        if self._db_conn is None:
            return 0
        try:
            return self._db_conn._protocol.queries_count
        except Exception:
            try:
                return self._db_conn._con._protocol.queries_count
            except Exception:
                pass
        return 0

    async def get_connection(self):
        if self._db_conn is None:
            self._db_conn = await self._manager._storage.open()
            self._query_count_start = self.get_query_count()
        return self._db_conn

    @property
    def strategy(self):
        return self._strategy

    @property
    def manager(self):
        return self._manager

    @property
    def storage(self):
        return self._manager._storage

    @property
    def objects_needing_invalidation(self):
        return self._objects_to_invalidate

    def get_before_commit_hooks(self):
        """ See ITransaction.
        """
        return iter(self._before_commit)

    def add_before_commit_hook(self, hook, *real_args, args=[], kws=None, **kwargs):
        """ See ITransaction.
        """
        if kws is None:
            kws = {}
        kwargs.update(kws)
        self._before_commit.append((hook, real_args + tuple(args), kwargs))

    def get_after_commit_hooks(self):
        """ See ITransaction.
        """
        return iter(self._after_commit)

    def add_after_commit_hook(self, hook, *real_args, args=[], kws=None, **kwargs):
        """ See ITransaction.
        """
        if kws is None:
            kws = {}
        kwargs.update(kws)
        self._after_commit.append((hook, real_args + tuple(args), kwargs))

    @profilable
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
                await lazy_apply(hook, status, *args, **kws)
            except:  # noqa
                # We need to catch the exceptions if we want all hooks
                # to be called
                logger.error("Error in after commit hook exec in %s ",
                             hook, exc_info=sys.exc_info())
        self._after_commit = []

    # BEGIN TXN
    async def tpc_begin(self):
        """Begin commit of a transaction

        conn is a real db that will be got by db.open()
        """
        self._txn_time = time.time()
        await self._strategy.tpc_begin()
        # make sure this is reset on retries
        self._after_commit = []
        self._before_commit = []

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

    @profilable
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
                new_oid = app_settings['oid_generator'](obj)
            oid = new_oid

        obj._p_oid = oid
        if new or obj.__new_marker__:
            self.added[oid] = obj
        elif oid not in self.modified and oid not in self.added:
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
        self._manager._hard_cache.clear()
        await self._cache.clear()

    async def refresh(self, ob):
        '''
        refresh an object with the value from the database
        '''
        new = await self.get(ob._p_oid, ignore_registered=True)
        for key, value in new.__dict__.items():
            if key.startswith('_p') or key.startswith('__'):
                continue
            ob.__dict__[key] = value
        ob._p_serial = new._p_serial

    @cache(lambda oid: {'oid': oid}, True)
    async def _get(self, oid):
        return await self._manager._storage.load(self, oid)

    @profilable
    async def get(self, oid, ignore_registered=False):
        """Getting a oid from the db"""
        if not ignore_registered:
            obj = self.modified.get(oid, None)
            if obj is not None:
                return obj

        result = self._manager._hard_cache.get(oid, None)
        if result is None:
            result = await self._get(oid)

        obj = reader(result)
        obj._p_jar = self
        if obj.__immutable_cache__:
            # ttl of zero means we want to provide a hard cache here
            self._manager._hard_cache[oid] = result

        return obj

    async def commit(self):
        restarts = 0
        while True:
            # for now, the max commit restarts we'll manage...
            try:
                return await self._commit()
            except RestartCommit:
                restarts += 1
                if restarts >= 3:
                    raise
                else:
                    logger.warn(f'Restarting commit for tid: {self._tid}')
                    await self._db_txn.restart()

    @profilable
    async def _commit(self):
        await self._call_before_commit_hooks()
        self.status = Status.COMMITTING
        try:
            if len(self.modified) > 0 or len(self.deleted) > 0 or len(self.added) > 0:
                # only do the commit steps if we have objects to commit
                await self.tpc_commit()
                # vote will do conflict resolution if there are conflicting writes
                await self.tpc_vote()
            else:
                # signal to not worry about not making a transaction here..
                self._skip_commit = True
            await self.tpc_finish()
        except (ConflictError, TIDConflictError) as ex:
            # this exception should bubble up
            # in the case of TIDConflictError, we should make sure to try
            # and invalidate again to make sure we aren't caching the ob
            self.status = Status.CONFLICT
            await self._manager._storage.abort(self)
            await self._cache.close(invalidate=isinstance(ex, TIDConflictError))
            self.tpc_cleanup()
            raise
        self.status = Status.COMMITTED
        await self._call_after_commit_hooks()

    @profilable
    async def abort(self):
        self.status = Status.ABORTED
        await self._manager._storage.abort(self)
        await self._cache.close(invalidate=False)
        self.tpc_cleanup()

    async def _call_before_commit_hooks(self):
        for hook, args, kws in self._before_commit:
            await lazy_apply(hook, *args, **kws)
        self._before_commit = []

    @profilable
    async def _store_object(self, obj, oid, added=False):
        # Modified objects
        if obj._p_jar is not self and obj._p_jar is not None:
            raise Exception('Invalid reference to txn')

        # There is no serial
        if added:
            serial = None
        else:
            serial = getattr(obj, "_p_serial", 0)

        writer = IWriter(obj)
        await self._manager._storage.store(oid, serial, writer, obj, self)
        obj._p_serial = self._tid
        obj._p_oid = oid
        if obj._p_jar is None:
            obj._p_jar = self
        self._objects_to_invalidate.append(obj)

    @profilable
    async def tpc_commit(self):
        """Commit changes to an object"""
        await self._strategy.tpc_commit()
        for oid, obj in self.added.items():
            await self._store_object(obj, oid, True)
            obj.__new_marker__ = False
        for oid, obj in self.modified.items():
            await self._store_object(obj, oid)
        for oid, obj in self.deleted.items():
            if obj._p_jar is not self and obj._p_jar is not None:
                raise Exception('Invalid reference to txn')
            await self._manager._storage.delete(self, oid)
            self._objects_to_invalidate.append(obj)

    @profilable
    async def tpc_vote(self):
        """Verify that a data manager can commit the transaction."""
        ok = await self._strategy.tpc_vote()
        if ok is False:
            raise ConflictError(self)

    @profilable
    async def tpc_finish(self):
        """Indicate confirmation that the transaction is done.
        """
        await self._strategy.tpc_finish()
        await self._cache.close()
        self.tpc_cleanup()

    def tpc_cleanup(self):
        self.added = {}
        self.modified = {}
        self.deleted = {}
        self._objects_to_invalidate = []
        self._db_txn = None

    # Inspection

    @profilable
    @cache(lambda oid: {'oid': oid, 'variant': 'keys'})
    async def keys(self, oid):
        keys = []
        for record in await self._manager._storage.keys(self, oid):
            keys.append(record['id'])
        return keys

    @cache(lambda container, key: {'container': container, 'id': key}, True)
    async def _get_child(self, container, key):
        return await self._manager._storage.get_child(self, container._p_oid, key)

    @profilable
    async def get_child(self, parent, key):
        result = await self._get_child(parent, key)
        if result is None:
            return None

        return self._fill_object(result, parent)

    def _fill_object(self, item, parent):
        obj = reader(item)
        obj.__parent__ = parent
        obj._p_jar = self
        return obj

    async def _get_batch_children(self, parent, keys):
        for litem in await self._manager._storage.get_children(
                self, parent._p_oid, keys):
            if len(litem['state']) < self._cache.max_cache_record_size:
                await self._cache.set(litem, container=parent, id=litem['id'])
                self._cache._stored += 1
            yield self._fill_object(litem, parent)

    async def get_children(self, parent, keys):
        '''
        More performant way to get groups of items.
        - look at cache
        - batch get from storage
        - async for iterate items
        - store retrieved values in storage
        '''
        lookup_group = []  # backlog of object that need to be looked up
        for key in keys:
            item = await self._cache.get(container=parent, id=key)
            if item is None:
                self._cache._misses += 1
                lookup_group.append(key)
                if len(lookup_group) > 15:  # limit batch size
                    async for litem in self._get_batch_children(parent, lookup_group):
                        yield litem
                    lookup_group = []
                continue

            self._cache._hits += 1
            if len(lookup_group) > 0:
                # we need to clear this buffer first before we can yield this item
                async for litem in self._get_batch_children(parent, lookup_group):
                    yield litem
                lookup_group = []

            yield self._fill_object(item, parent)

        # flush the rest
        if len(lookup_group) > 0:
            async for item in self._get_batch_children(parent, lookup_group):
                yield item

    @profilable
    async def contains(self, oid, key):
        return await self._manager._storage.has_key(self, oid, key)  # noqa

    @profilable
    @cache(lambda oid: {'oid': oid, 'variant': 'len'})
    async def len(self, oid):
        return await self._manager._storage.len(self, oid)

    @profilable
    async def items(self, container):
        # XXX not using cursor because we can't cache with cursor results...
        keys = await self.keys(container._p_oid)
        async for item in self.get_children(container, keys):
            yield item.__name__, item

    @profilable
    @cache(lambda base_obj, id: {'container': base_obj, 'id': id, 'variant': 'annotation'}, True)
    async def _get_annotation(self, base_obj, id):
        result = await self._manager._storage.get_annotation(self, base_obj._p_oid, id)
        if result is None:
            return _EMPTY
        return result

    @profilable
    async def get_annotation(self, base_obj, id):
        result = await self._get_annotation(base_obj, id)
        if result == _EMPTY:
            raise KeyError(id)
        obj = reader(result)
        obj.__of__ = base_obj._p_oid
        obj._p_jar = self
        return obj

    @profilable
    @cache(lambda oid: {'oid': oid, 'variant': 'annotation-keys'})
    async def get_annotation_keys(self, oid):
        return [r['id'] for r in
                await self._manager._storage.get_annotation_keys(self, oid)]

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

    async def get_total_resources_of_type(self, type_):
        return await self._manager._storage.get_total_resources_of_type(
            self, type_)

    async def _get_resources_of_type(self, type_, page_size=1000):
        page = 1
        keys = await self._manager._storage._get_page_resources_of_type(
            self, type_, page=page, page_size=page_size)
        while len(keys) > 0:
            for key in keys:
                yield key
            page += 1
            keys = await self._manager._storage._get_page_resources_of_type(
                self, type_, page=page, page_size=page_size)

    async def get_page_of_keys(self, parent_oid, page=1, page_size=1000):
        return await self._manager._storage.get_page_of_keys(
            self, parent_oid, page=page, page_size=page_size)

    @profilable
    async def iterate_keys(self, oid, page_size=1000):
        page = 1
        keys = await self._manager._storage.get_page_of_keys(
            self, oid, page=page, page_size=page_size)
        while len(keys) > 0:
            for key in keys:
                yield key
            page += 1
            keys = await self._manager._storage.get_page_of_keys(
                self, oid, page=page, page_size=page_size)
