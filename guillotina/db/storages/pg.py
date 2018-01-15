from asyncio import shield
from guillotina import app_settings
from guillotina.db.interfaces import IStorage
from guillotina.db.storages import sql
from guillotina.db.storages.base import BaseStorage
from guillotina.db.storages.sql import Column
from guillotina.db.storages.sql import Index
from guillotina.db.storages.sql import Sequence
from guillotina.db.storages.sql import SQL
from guillotina.db.storages.sql import Table
from guillotina.exceptions import ConflictError
from guillotina.exceptions import TIDConflictError
from guillotina.profile import profilable
from zope.interface import implementer

import asyncio
import asyncpg
import asyncpg.connection
import concurrent
import logging
import time
import ujson


log = logging.getLogger("guillotina.storage")

# we can not use FOR UPDATE or FOR SHARE unfortunately because
# it can cause deadlocks on the database--we need to resolve them ourselves
GET_OID = SQL("""
SELECT zoid, tid, state_size, resource, of, parent_id, id, type, state
FROM {table}
WHERE zoid = $1::varchar(32)
""")

GET_CHILDREN_KEYS = SQL("""
SELECT id
FROM {table}
WHERE parent_id = $1::varchar(32)
""")


GET_ANNOTATIONS_KEYS = SQL("""
SELECT id
FROM {table}
WHERE of = $1::varchar(32) AND (parent_id IS NULL OR parent_id != '{trashed_id}')
""")


GET_CHILD = SQL("""
SELECT zoid, tid, state_size, resource, type, state, id
FROM {table}
WHERE parent_id = $1::varchar(32) AND id = $2::text
""")


EXIST_CHILD = SQL("""
SELECT zoid
FROM {table}
WHERE parent_id = $1::varchar(32) AND id = $2::text
""")


HAS_OBJECT = SQL("""
SELECT zoid, part
FROM {table}
WHERE zoid = $1::varchar(32)
""")


GET_ANNOTATION = SQL("""
SELECT zoid, tid, state_size, resource, type, state, id
FROM {table}
WHERE
    of = $1::varchar(32) AND
    id = $2::text AND
    (parent_id IS NULL OR parent_id != '{trashed_id}')
""")

def _wrap_return_count(txt):
    return """WITH rows AS (
{}
    RETURNING 1
)
SELECT count(*) FROM rows""".format(txt)


# upsert without checking matching tids on updated object
INSERT = SQL(_wrap_return_count("""
INSERT INTO {table}
(zoid, tid, state_size, part, resource, of, otid, parent_id, id, type, json, state)
VALUES ($1::varchar(32), $2::int, $3::int, $4::int, $5::boolean, $6::varchar(32), $7::int,
        $8::varchar(32), $9::text, $10::text, $11::json, $12::bytea)
"""))


# update without checking matching tids on updated object
UPDATE = SQL(_wrap_return_count("""
UPDATE {table}
SET
    tid = $2::int,
    state_size = $3::int,
    part = $4::int,
    resource = $5::boolean,
    of = $6::varchar(32),
    otid = $7::int,
    parent_id = $8::varchar(32),
    id = $9::text,
    type = $10::text,
    json = $11::json,
    state = $12::bytea
WHERE
    zoid = $1::varchar(32) AND tid = $7::int"""))


NEXT_TID = SQL("SELECT nextval('tid_sequence');")
MAX_TID = SQL("SELECT last_value FROM tid_sequence;")


NUM_CHILDREN = SQL("SELECT count(*) FROM {table} WHERE parent_id = $1::varchar(32)")

RESOURCES_BY_TYPE = SQL("""
SELECT zoid, tid, state_size, resource, type, state, id
FROM {table}
WHERE type=$1::TEXT
ORDER BY zoid
LIMIT $2::int
OFFSET $3::int
""")


GET_CHILDREN = SQL("""
SELECT zoid, tid, state_size, resource, type, state, id
FROM {table}
WHERE parent_id = $1::VARCHAR(32)
""")


GET_CHILDREN_BATCH = SQL("""
SELECT zoid, tid, state_size, resource, type, state, id
FROM {table}
WHERE parent_id = $1::varchar(32) AND id = ANY($2)
""")


TRASH_PARENT_ID = SQL("""
UPDATE {table}
SET
    parent_id = '{trashed_id}'
WHERE
    zoid = $1::varchar(32)
""")


INSERT_BLOB_CHUNK = SQL("""
INSERT INTO {table}
(bid, zoid, chunk_index, data, part)
VALUES ($1::VARCHAR(32), $2::VARCHAR(32), $3::INT, $4::BYTEA, $5::BIGINT)
""", 'blobs')


READ_BLOB_CHUNKS = SQL("""
SELECT * from {table}
WHERE bid = $1::VARCHAR(32)
ORDER BY chunk_index
""", 'blobs')

READ_BLOB_CHUNK = SQL("""
SELECT * from {table}
WHERE bid = $1::VARCHAR(32)
AND chunk_index = $2::int
""", 'blobs')


DELETE_BLOB = SQL("""
DELETE FROM {table} WHERE bid = $1::VARCHAR(32);
""", 'blobs')


TXN_CONFLICTS = SQL("""
SELECT zoid, tid, state_size, resource, type, id
FROM {table}
WHERE tid > $1""")
TXN_CONFLICTS_ON_OIDS = SQL(TXN_CONFLICTS.sql + ' AND zoid = ANY($2)')


BATCHED_GET_CHILDREN_KEYS = SQL("""
SELECT id
FROM {table}
WHERE parent_id = $1::varchar(32)
ORDER BY zoid
LIMIT $2::int
OFFSET $3::int
""")

DELETE_OBJECT = SQL("""
DELETE FROM {table}
WHERE zoid = $1::varchar(32);
""")

CREATE_TRASH = SQL('''
INSERT INTO {table} (zoid, tid, state_size, part, resource, type)
SELECT '{trashed_id}', 0, 0, 0, FALSE, 'TRASH_REF'
WHERE NOT EXISTS (SELECT * FROM {table} WHERE zoid = '{trashed_id}')
RETURNING id;
''')

DROP_BLOBS = SQL("DROP TABLE IF EXISTS {table};", 'blobs')
DROP_OBJECTS = SQL("DROP TABLE IF EXISTS {table};")

DELETE_BY_PARENT_OID = SQL('''DELETE FROM {table}
WHERE parent_id = $1::varchar(32);''')
DELETE_FROM_BLOBS = SQL(
    "DELETE FROM {table} WHERE zoid = $1::varchar(32);", 'blobs')

BATCHED_GET_CHILDREN_OIDS = SQL("""
SELECT zoid FROM {table}
WHERE parent_id = $1::varchar(32)
ORDER BY zoid
LIMIT $2::int
OFFSET $3::int;""")

# how long to wait before trying to recover bad connections
BAD_CONNECTION_RESTART_DELAY = 0.25


class LightweightConnection(asyncpg.connection.Connection):
    '''
    See asyncpg.connection.Connection._get_reset_query to see
    details of the point of this.
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # we purposefully do not support these options for performance
        self._server_caps = asyncpg.connection.ServerCapabilities(
            advisory_locks=False,
            notifications=False,
            sql_reset=False,
            sql_close_all=False,
            plpgsql=self._server_caps.plpgsql
        )

    async def add_listener(self, channel, callback):
        raise NotImplemented('Does not support listeners')

    async def remove_listener(self, channel, callback):
        raise NotImplemented('Does not support listeners')


async def iterate_children(conn, parent_oid, page_size=1000):
    smt = await conn.prepare(BATCHED_GET_CHILDREN_OIDS.render())
    page = 1
    results = await smt.fetch(parent_oid, page_size, (page - 1) * page_size)
    while len(results) > 0:
        for record in results:
            yield record['zoid']
        page += 1
        results = await smt.fetch(parent_oid, page_size, (page - 1) * page_size)


class PGVacuum:
    '''
    Since cascade on delete can be very slow, when we delete on object,
    we actual set it's parent_id to a placeholder to make sure the delete
    transaction finishes fast.

    Then in this vacuum task, we do cleanup with autocommit mode.
    '''

    _delete_by_parent_oid = DELETE_BY_PARENT_OID
    _delete_from_blobs = DELETE_FROM_BLOBS

    def __init__(self, storage, loop):
        self._storage = storage
        self._loop = loop
        self._queue = asyncio.Queue(loop=loop)
        self._active = False
        self._closed = False

    async def vacuum_children(self, conn, parent_oid):
        async for child_oid in iterate_children(conn, parent_oid):
            await self.vacuum_children(conn, child_oid)
        await conn.execute(self._delete_by_parent_oid.render(), parent_oid)
        await conn.execute(self._delete_from_blobs.render(), parent_oid)

    @property
    def active(self):
        return self._active

    async def initialize(self):
        while not self._closed:
            try:
                await self._initialize()
            except (concurrent.futures.CancelledError, RuntimeError):
                # we're okay with the task getting cancelled
                return
            finally:
                self._active = True

    async def _initialize(self):
        # get existing trashed objects, push them on the queue...
        # there might be contention, but that is okay

        while not self._closed:
            oid = None
            try:
                oid = await self._queue.get()
                self._active = True
                await self.vacuum(oid)
            except (concurrent.futures.CancelledError, RuntimeError):
                raise
            except Exception:
                log.warning(f'Error vacuuming oid {oid}', exc_info=True)
            finally:
                self._active = False
                try:
                    self._queue.task_done()
                except ValueError:
                    pass

    async def add_to_queue(self, oid):
        await self._queue.put(oid)

    async def vacuum(self, oid):
        '''
        Recursively go through objects, deleting children as you find them,
        checking if they have their own children and so on...

        Once cockroachdb 2.0 is stable, we can remove this custom vacuum implementation.
        '''
        conn = await self._storage.open()
        try:
            await self.vacuum_children(conn, oid)
        finally:
            try:
                await self._storage.close(conn)
            except asyncpg.exceptions.ConnectionDoesNotExistError:
                pass

    async def finalize(self):
        self._closed = True
        await self._queue.join()
        # wait for up to two seconds to finish the task...
        # it's not long but we don't want to wait for a long time to close either....
        try:
            await asyncio.wait_for(self.wait_until_no_longer_active(), 2)
        except asyncio.TimeoutError:
            pass
        except concurrent.futures.CancelledError:
            # we do not care if it's cancelled... things will get cleaned up
            # in a future task anyways...
            pass

    async def wait_until_no_longer_active(self):
        while self._active:
            # give it a chance to finish...
            await asyncio.sleep(0.1)


@implementer(IStorage)
class PostgresqlStorage(BaseStorage):
    """Storage to a relational database, based on invalidation polling"""

    _dsn = None
    _pool_size = None
    _pool = None
    _large_record_size = 1 << 24
    _vacuum_class = PGVacuum
    _partitioning_supported = True

    _object_table = Table('objects', [
        Column('zoid', sql.VARCHAR(32), not_null=True),
        Column('tid', sql.BIGINT, not_null=True),
        Column('state_size', sql.BIGINT, not_null=True),
        Column('part', sql.BIGINT, not_null=True),
        Column('resource', sql.BOOLEAN, not_null=True),
        Column('of', sql.VARCHAR(32)),
        Column('otid', sql.BIGINT),
        Column('parent_id', sql.VARCHAR(32)),
        Column('id', sql.TEXT),
        Column('type', sql.TEXT, not_null=True),
        Column('json', sql.JSONB),
        Column('state', sql.BYTEA),
    ], indexes=[
        Index('object_tid', 'tid'),
        Index('object_of', 'of'),
        Index('object_part', 'part'),
        Index('object_parent', 'parent_id'),
        Index('object_id', 'id'),
        Index('object_type', 'type')
    ])
    _blob_table = Table('blobs', [
        Column('bid', sql.VARCHAR(32), not_null=True),
        Column('zoid', sql.VARCHAR(32), not_null=True),
        Column('chunk_index', sql.INT, not_null=True),
        Column('data', sql.BYTEA),
        Column('part', sql.BIGINT, not_null=True),
    ], indexes=[
        Index('blob_bid', 'bid'),
        Index('blob_zoid', 'zoid'),
        Index('blob_chunk', 'chunk_index'),
    ])

    _statements = [
        Sequence('tid_sequence')
    ]

    def __init__(self, dsn=None, read_only=False, name=None,
                 pool_size=13, transaction_strategy='resolve_readcommitted',
                 conn_acquire_timeout=20, cache_strategy='dummy', **options):
        super(PostgresqlStorage, self).__init__(
            read_only, transaction_strategy=transaction_strategy,
            cache_strategy=cache_strategy)
        self._dsn = dsn
        self._pool_size = pool_size
        self._read_only = read_only
        self.__name__ = name
        self._read_conn = None
        self._lock = asyncio.Lock()
        self._conn_acquire_timeout = conn_acquire_timeout
        self._options = options
        self._connection_options = {}
        self._connection_initialized_on = time.time()
        self._known_partitions = []

    async def finalize(self):
        await self._vacuum.finalize()
        self._vacuum_task.cancel()
        try:
            await shield(self._pool.release(self._read_conn))
        except asyncpg.exceptions.InterfaceError:
            pass
        await self._pool.close()

    async def _create_table(self, table):
        try:
            async with self._lock:
                statements = '\n'.join([str(s) for s in table.get_statements()])
                print(statements)
                await self._read_conn.execute(statements)
        except asyncpg.exceptions.UniqueViolationError:
            # this is okay on creation, means 2 getting created at same time
            pass

    async def _create_partition(self, table, partition=0):
        async with self._lock:
            for statement in table.get_statements(partition=partition):
                print(statement)
                await self._read_conn.execute(statement)
        self._known_partitions.append(partition)

    async def create(self):
        await self._create_table(self._object_table, partitioning_support=self._partitioning_supported)
        await self._create_table(self._blob_table, partitioning_support=self._partitioning_supported)
        if self._partitioning_supported:
            await self._create_partition(self._object_table)
            await self._create_partition(self._blob_table)
        await self._read_conn.execute(CREATE_TRASH.render())
        for statement in self._statements:
            try:
                await self._read_conn.execute(str(statement))
            except asyncpg.exceptions.UniqueViolationError:
                # this is okay on creation, means 2 getting created at same time
                pass

    async def restart_connection(self):
        log.error('Connection potentially lost to pg, restarting')
        await self._pool.close()
        self._pool.terminate()
        # re-bind, throw conflict error so the request is restarted...
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            max_size=self._pool_size,
            min_size=2,
            loop=self._pool._loop,
            connection_class=app_settings['pg_connection_class'],
            **self._connection_options)

        # shared read connection on all transactions
        self._read_conn = await self.open()
        await self.initialize_tid_statements()
        self._connection_initialized_on = time.time()
        raise ConflictError('Restarting connection to postgresql')

    async def initialize(self, loop=None, **kw):
        self._connection_options = kw
        if loop is None:
            loop = asyncio.get_event_loop()
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            max_size=self._pool_size,
            min_size=2,
            connection_class=app_settings['pg_connection_class'],
            loop=loop,
            **kw)

        # shared read connection on all transactions
        self._read_conn = await self.open()
        try:
            await self.initialize_tid_statements()
        except asyncpg.exceptions.UndefinedTableError:
            await self.create()
            await self.initialize_tid_statements()

        self._vacuum = self._vacuum_class(self, loop)
        self._vacuum_task = asyncio.Task(self._vacuum.initialize(), loop=loop)

        def vacuum_done(task):
            if self._vacuum._closed:
                # if it's closed, we know this is expected
                return
            log.warning('Vacuum pg task ended. This should not happen. '
                        'No database vacuuming will be done here anymore.')

        self._vacuum_task.add_done_callback(vacuum_done)
        self._connection_initialized_on = time.time()

    async def initialize_tid_statements(self):
        self._stmt_next_tid = await self._read_conn.prepare(NEXT_TID.render())
        self._stmt_max_tid = await self._read_conn.prepare(MAX_TID.render())

    async def remove(self):
        """Reset the tables"""
        async with self._pool.acquire() as conn:
            await conn.execute(DROP_BLOBS.render())
            await conn.execute(DROP_OBJECTS.render())

    async def open(self):
        try:
            conn = await self._pool.acquire(timeout=self._conn_acquire_timeout)
        except asyncpg.exceptions.InterfaceError as ex:
            async with self._lock:
                await self._check_bad_connection(ex)
        return conn

    async def close(self, con):
        try:
            await shield(self._pool.release(con))
        except (asyncio.CancelledError, asyncpg.exceptions.ConnectionDoesNotExistError,
                RuntimeError):
            pass

    async def load(self, txn, oid):
        async with txn._lock:
            smt = await txn._db_conn.prepare(GET_OID.render())
            objects = await self.get_one_row(smt, oid)
        if objects is None:
            raise KeyError(oid)
        return objects

    async def _get_store_statement(self, txn, obj, update=UPDATE, insert=INSERT):
        if self._partitioning_supported:
            if obj.__part_id__ not in self._known_partitions:
                await self._create_partition(self._object_table, obj.__part_id__)
                await self._create_partition(self._blob_table, obj.__part_id__)

        update = False
        statement_sql = insert
        if not obj.__new_marker__ and obj._p_serial is not None:
            # we should be confident this is an object update
            statement_sql = update
            update = True
        async with txn._lock:
            smt = await txn._db_conn.prepare(statement_sql.render(ob=obj))
        return smt, update

    @profilable
    async def store(self, oid, old_serial, writer, obj, txn):
        assert oid is not None

        pickled = writer.serialize()  # This calls __getstate__ of obj
        if len(pickled) >= self._large_record_size:
            log.warning(f"Large object {obj.__class__}: {len(pickled)}")
        json_dict = await writer.get_json()
        json = ujson.dumps(json_dict)
        part = writer.part
        if part is None:
            part = 0

        smt, update = await self._get_store_statement(txn, obj)
        async with txn._lock:
            try:
                result = await smt.fetch(
                    oid,                 # The OID of the object
                    txn._tid,            # Our TID
                    len(pickled),        # Len of the object
                    part,                # Partition indicator
                    writer.resource,     # Is a resource ?
                    writer.of,           # It belogs to a main
                    old_serial,          # Old serial
                    writer.parent_id,    # Parent OID
                    writer.id,           # Traversal ID
                    writer.type,         # Guillotina type
                    json,                # JSON catalog
                    pickled              # Pickle state)
                )
            except asyncpg.exceptions.ForeignKeyViolationError:
                txn.deleted[obj._p_oid] = obj
                raise TIDConflictError(
                    f'Bad value inserting into database that could be caused '
                    f'by a bad cache value. This should resolve on request retry.',
                    oid, txn, old_serial, writer)
            except asyncpg.exceptions._base.InterfaceError as ex:
                if 'another operation is in progress' in ex.args[0]:
                    raise ConflictError(
                        f'asyncpg error, another operation in progress.',
                        oid, txn, old_serial, writer)
                raise
            except asyncpg.exceptions.DeadlockDetectedError:
                raise ConflictError(f'Deadlock detected.',
                                    oid, txn, old_serial, writer)
            if len(result) != 1 or result[0]['count'] != 1:
                if update:
                    # raise tid conflict error
                    raise TIDConflictError(
                        f'Mismatch of tid of object being updated. This is likely '
                        f'caused by a cache invalidation race condition and should '
                        f'be an edge case. This should resolve on request retry.',
                        oid, txn, old_serial, writer)
                else:
                    log.error('Incorrect response count from database update. '
                              'This should not happen. tid: {}'.format(txn._tid))
        await txn._cache.store_object(obj, pickled)

    async def _txn_oid_commit_hook(self, status, oid):
        await self._vacuum.add_to_queue(oid)

    async def _txn_drop_db_commit_hook(self, status, partition):
        async with self._lock:
            await self._read_conn.execute(self._object_table.drop(partition))

    async def delete(self, txn, ob):
        # no cascade support, so we push to vacuum
        async with txn._lock:
            await txn._db_conn.execute(DELETE_OBJECT.render(ob=ob), ob._p_oid)
            await txn._db_conn.execute(DELETE_FROM_BLOBS.render(ob=ob), ob._p_oid)
        if self._partitioning_supported:
            partitioner = app_settings['partitioner'](ob)
            if partitioner.root:
                # root of paritition so we just drop the whole table and do not
                # do the whole recursive delete thing
                txn.add_after_commit_hook(
                    self._txn_drop_db_commit_hook, [partitioner.part_id])
                return
        txn.add_after_commit_hook(self._txn_oid_commit_hook, [ob._p_oid])

    async def _check_bad_connection(self, ex):
        if str(ex) in ('cannot perform operation: connection is closed',
                       'connection is closed', 'pool is closed'):
            if (time.time() - self._connection_initialized_on) > BAD_CONNECTION_RESTART_DELAY:
                # we need to make sure we aren't calling this over and over again
                return await self.restart_connection()

    async def get_next_tid(self, txn):
        async with self._lock:
            # we do not use transaction lock here but a storage lock because
            # a storage object has a shard conn for reads
            try:
                return await self._stmt_next_tid.fetchval()
            except asyncpg.exceptions.InterfaceError as ex:
                await self._check_bad_connection(ex)
                raise

    async def get_current_tid(self, txn):
        async with self._lock:
            # again, use storage lock here instead of trns lock
            return await self._stmt_max_tid.fetchval()

    async def get_one_row(self, smt, *args):
        # Helper function to provide easy adaptation to cockroach
        return await smt.fetchrow(*args)

    def _db_transaction_factory(self, txn):
        # make sure asycpg knows this is a new transaction
        if txn._db_conn._con is not None:
            txn._db_conn._con._top_xact = None
        return txn._db_conn.transaction(readonly=txn._manager._storage._read_only)

    async def start_transaction(self, txn, retries=0):
        error = None
        async with txn._lock:
            try:
                txn._db_txn = self._db_transaction_factory(txn)
            except asyncpg.exceptions.InterfaceError as ex:
                async with self._lock:
                    await self._check_bad_connection(ex)
                raise
            try:
                await txn._db_txn.start()
                return
            except (asyncpg.exceptions.InterfaceError,
                    asyncpg.exceptions.InternalServerError) as ex:
                error = ex

        if error is not None:
            if retries > 2:
                raise error

            restart = rollback = False
            if isinstance(error, asyncpg.exceptions.InternalServerError):
                restart = True
                if error.sqlstate == 'XX000':
                    rollback = True
            elif ('manually started transaction' in error.args[0] or
                    'connection is closed' in error.args[0]):
                restart = True
                if 'manually started transaction' in error.args[0]:
                    rollback = True

            if rollback:
                try:
                    # thinks we're manually in txn, manually rollback and try again...
                    await txn._db_conn.execute('ROLLBACK;')
                except asyncpg.exceptions._base.InterfaceError:
                    # we're okay with this error here...
                    pass
            if restart:
                await self.close(txn._db_conn)
                txn._db_conn = await self.open()
                return await self.start_transaction(txn, retries + 1)

    async def get_conflicts(self, txn):
        # XXX Might be slow because we need to check conflicts against all tables?
        async with self._lock:
            # use storage lock instead of transaction lock
            if len(txn.modified) < 1000:
                # if it's too large, we're not going to check on object ids
                modified_oids = [k for k in txn.modified.keys()]
                return await self._read_conn.fetch(
                    TXN_CONFLICTS_ON_OIDS.render(), txn._tid, modified_oids)
            else:
                return await self._read_conn.fetch(TXN_CONFLICTS.render(), txn._tid)

    async def commit(self, transaction):
        if transaction._db_txn is not None:
            async with transaction._lock:
                await transaction._db_txn.commit()
        elif self._transaction_strategy not in ('none', 'tidonly'):
            log.warning('Do not have db transaction to commit')
        return transaction._tid

    async def abort(self, transaction):
        if transaction._db_txn is not None:
            async with transaction._lock:
                try:
                    await transaction._db_txn.rollback()
                except asyncpg.exceptions._base.InterfaceError:
                    # we're okay with this error here...
                    pass
        # reads don't need transaction necessarily so don't log
        # else:
        #     log.warning('Do not have db transaction to rollback')

    # Introspection
    async def get_page_of_keys(self, txn, ob, page=1, page_size=1000):
        conn = txn._db_conn
        smt = await conn.prepare(BATCHED_GET_CHILDREN_KEYS.render(ob=ob))
        keys = []
        for record in await smt.fetch(ob._p_oid, page_size, (page - 1) * page_size):
            keys.append(record['id'])
        return keys

    async def keys(self, txn, ob):
        async with txn._lock:
            smt = await txn._db_conn.prepare(GET_CHILDREN_KEYS.render(ob=ob))
            result = await smt.fetch(ob._p_oid)
        return result

    async def get_child(self, txn, parent, id):
        async with txn._lock:
            smt = await txn._db_conn.prepare(GET_CHILD.render(ob=parent))
            result = await self.get_one_row(smt, parent._p_oid, id)
        return result

    async def get_children(self, txn, parent, ids):
        async with txn._lock:
            return await self._read_conn.fetch(
                GET_CHILDREN_BATCH.render(ob=parent), parent._p_oid, ids)

    async def has_key(self, txn, parent, id):
        async with txn._lock:
            smt = await txn._db_conn.prepare(EXIST_CHILD.render(ob=parent))
            result = await self.get_one_row(smt, parent._p_oid, id)
        if result is None:
            return False
        else:
            return True

    async def len(self, txn, ob):
        async with txn._lock:
            smt = await txn._db_conn.prepare(NUM_CHILDREN.render(ob=ob))
            result = await smt.fetchval(ob._p_oid)
        return result

    async def items(self, txn, ob):
        async with txn._lock:
            smt = await txn._db_conn.prepare(GET_CHILDREN.render(ob=ob))
        async for record in smt.cursor(ob._p_oid):
            # locks are dangerous in cursors since comsuming code might do
            # sub-queries and they you end up with a deadlock
            yield record

    async def get_annotation(self, txn, base_obj, id):
        async with txn._lock:
            smt = await txn._db_conn.prepare(GET_ANNOTATION.render(ob=base_obj))
            result = await self.get_one_row(smt, base_obj._p_oid, id)
        return result

    async def get_annotation_keys(self, txn, obj):
        async with txn._lock:
            smt = await txn._db_conn.prepare(GET_ANNOTATIONS_KEYS.render(ob=obj))
            result = await smt.fetch(obj._p_oid)
        return result

    async def write_blob_chunk(self, txn, bid, ob, chunk_index, data):

        async with txn._lock:
            smt = await txn._db_conn.prepare(HAS_OBJECT.render(ob=ob))
            result = await self.get_one_row(smt, ob._p_oid)
        if result is None:
            # check if we have a referenced ob, could be new and not in db yet.
            # if so, create a stub for it here...
            async with txn._lock:
                await txn._db_conn.execute('''INSERT INTO objects
                    (zoid, tid, state_size, part, resource, type)
                    VALUES ($1::varchar(32), -1, 0, 0, TRUE, 'stub')''', ob._p_oid)
            part = 0
        else:
            part = result['part']
        async with txn._lock:
            return await txn._db_conn.execute(
                INSERT_BLOB_CHUNK.render(), bid, ob._p_oid, chunk_index, data, part)

    async def read_blob_chunk(self, txn, bid, ob, chunk=0):
        async with txn._lock:
            smt = await txn._db_conn.prepare(READ_BLOB_CHUNK.render(ob=ob))
            return await self.get_one_row(smt, bid, chunk)

    async def read_blob_chunks(self, txn, bid, ob):
        async with txn._lock:
            smt = await txn._db_conn.prepare(READ_BLOB_CHUNKS.render(ob=ob))
        async for record in smt.cursor(bid):
            # locks are dangerous in cursors since comsuming code might do
            # sub-queries and they you end up with a deadlock
            yield record

    async def del_blob(self, txn, bid, ob):
        async with txn._lock:
            await txn._db_conn.execute(DELETE_BLOB.render(ob=ob), bid)

    # Massive treatment without security
    async def _get_page_resources_of_type(self, txn, type_, page, page_size):
        conn = txn._db_conn
        async with txn._lock:
            smt = await conn.prepare(RESOURCES_BY_TYPE.render())
        keys = []
        for record in await smt.fetch(type_, page_size, (page - 1) * page_size):  # noqa
            keys.append(record)
        return keys
