from guillotina.db.storages import pg
from guillotina.exceptions import ConflictError
from guillotina.exceptions import TIDConflictError

import asyncio
import asyncpg
import concurrent
import logging


logger = logging.getLogger('guillotina')

# upsert without checking matching tids on updated object
NAIVE_UPSERT = """
INSERT INTO objects
(zoid, tid, state_size, part, resource, of, otid, parent_id, id, type, state)
VALUES ($1::varchar(32), $2::int, $3::int, $4::int, $5::boolean, $6::varchar(32), $7::int,
        $8::varchar(32), $9::text, $10::text, $11::bytea)
ON CONFLICT (zoid)
DO UPDATE SET
    tid = EXCLUDED.tid,
    state_size = EXCLUDED.state_size,
    part = EXCLUDED.part,
    resource = EXCLUDED.resource,
    of = EXCLUDED.of,
    otid = EXCLUDED.otid,
    parent_id = EXCLUDED.parent_id,
    id = EXCLUDED.id,
    type = EXCLUDED.type,
    state = EXCLUDED.state"""
UPSERT = NAIVE_UPSERT + """
    WHERE
        tid = EXCLUDED.otid"""


# update without checking matching tids on updated object
UPDATE = """
UPDATE objects
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
    state = $11::bytea
WHERE
    zoid = $1::varchar(32)
    AND tid = $7::int
RETURNING tid, otid"""


NEXT_TID = """SELECT unique_rowid()"""
MAX_TID = "SELECT COALESCE(MAX(tid), 0) from objects;"

DELETE_FROM_BLOBS = """DELETE FROM blobs WHERE zoid = $1::varchar(32);"""
DELETE_CHILDREN = """DELETE FROM objects where parent_id = $1::varchar(32);"""
DELETE_DANGLING = '''DELETE FROM objects
WHERE
    parent_id IS NOT NULL and parent_id NOT IN (
        SELECT zoid FROM objects
    )
RETURNING 1
'''
DELETE_BY_PARENT_OID = '''DELETE FROM objects
WHERE parent_id = $1::varchar(32);'''
GET_OIDS_BY_PARENT = '''SELECT zoid FROM objects
WHERE parent_id = $1::varchar(32);'''
BATCHED_GET_CHILDREN_OIDS = """SELECT zoid FROM objects
WHERE parent_id = $1::varchar(32)
ORDER BY zoid
LIMIT $2::int
OFFSET $3::int"""


async def iterate_children(conn, parent_oid, page_size=1000):
    smt = await conn.prepare(BATCHED_GET_CHILDREN_OIDS)
    page = 1
    results = await smt.fetch(parent_oid, page_size, (page - 1) * page_size)
    while len(results) > 0:
        for record in results:
            yield record['zoid']
        page += 1
        results = await smt.fetch(parent_oid, page_size, (page - 1) * page_size)


class CockroachVacuum:

    def __init__(self, storage, loop):
        self._storage = storage
        self._loop = loop
        self._queue = asyncio.Queue(loop=loop)
        self._active = False
        self._closed = False

    @property
    def active(self):
        return self._active

    async def initialize(self):
        while not self._closed:
            oid = await self._queue.get()
            try:
                self._active = True
                await self.vacuum(oid)
            except concurrent.futures.CancelledError:
                pass  # task was cancelled, probably because we're shutting down
            except Exception:
                logger.warning(f'Error vacuuming oid {oid}', exc_info=True)
            finally:
                self._active = False
                self._queue.task_done()

    async def add_to_queue(self, oid):
        await self._queue.put(oid)

    async def vacuum_children(self, conn, parent_oid):
        async for child_oid in iterate_children(conn, parent_oid):
            await self.vacuum_children(conn, child_oid)
        await conn.execute(DELETE_BY_PARENT_OID, parent_oid)

    async def vacuum(self, oid):
        '''
        Options for vacuuming...
        1. Recursively go through objects, deleting children as you find them,
           checking if they have their own children and so on...
           - possibly more ram usage
           - more application logic
           - need to batch children
        2. Delete initial children, then delete objects that are dangling(parent_id missing)
           - less error prone
           - self-correcting(will correct deletes that went wrong before)
           - more overhead on cockroach

        We're choosing #1 for now....

        Long term, might need a combination of both
        '''
        conn = await self._storage.open()
        try:
            await self.vacuum_children(conn, oid)
        finally:
            await self._storage.close(conn)

    async def finalize(self):
        self._closed = True
        await self._queue.join()
        while self._active:
            # give it a chance to finish...
            await asyncio.sleep(0.1)


class CockroachDBTransaction:

    def __init__(self, txn):
        self._txn = txn
        self._conn = txn._db_conn
        self._storage = txn._manager._storage
        self._status = 'none'
        self._priority = 'LOW'
        if txn.request is not None:
            attempts = getattr(txn.request, '_retry_attempt', 0)
            if attempts == 1:
                self._priority = 'NORMAL'
            elif attempts > 1:
                self._priority = 'HIGH'

    async def start(self):
        assert self._status in ('none',)
        await self._conn.execute(f'''
BEGIN ISOLATION LEVEL {self._storage._isolation_level.upper()},
      PRIORITY {self._priority};''')
        self._status = 'started'

    async def commit(self):
        assert self._status in ('started',)
        await self._conn.execute('COMMIT;')
        self._status = 'committed'

    async def rollback(self):
        assert self._status in ('started',)
        try:
            await self._conn.execute('ROLLBACK;')
        except asyncpg.exceptions.InternalServerError as ex:
            # already aborted...
            pass
        self._status = 'rolledback'


class CockroachStorage(pg.PostgresqlStorage):
    '''
    Differences that we use from postgresql:
        - no jsonb support
        - no CASCADE support(ON DELETE CASCADE)
            - used by objects and blobs tables
            - right now, deleting will potentially leave dangling rows around
            - potential solutions
                - utility to recursively delete?
                - complex delete from query that does the sub queries to delete?
        - no sequence support
            - use serial construct of unique_rowid() instead
        - no referencial integrity support!
            - because we can't do ON DELETE support of any kind, we would get
              errors after we run deletes unless we walk the whole sub tree
              first, which is costly
            - so we need to manually clean it up in a task that runs periodically,
              our own db vacuum task.
    '''

    _object_schema = pg.PostgresqlStorage._object_schema.copy()
    del _object_schema['json']  # no json db support
    _object_schema.update({
        'of': 'VARCHAR(32)',
        'parent_id': 'VARCHAR(32)'
    })

    _blob_schema = pg.PostgresqlStorage._blob_schema.copy()
    _blob_schema.update({
        'zoid': 'VARCHAR(32) NOT NULL',
    })

    _initialize_statements = [
        'CREATE INDEX IF NOT EXISTS object_tid ON objects (tid);',
        'CREATE INDEX IF NOT EXISTS object_of ON objects (of);',
        'CREATE INDEX IF NOT EXISTS object_part ON objects (part);',
        'CREATE INDEX IF NOT EXISTS object_parent ON objects (parent_id);',
        'CREATE INDEX IF NOT EXISTS object_id ON objects (id);',
        'CREATE INDEX IF NOT EXISTS blob_bid ON blobs (bid);',
        'CREATE INDEX IF NOT EXISTS blob_zoid ON blobs (zoid);',
        'CREATE INDEX IF NOT EXISTS blob_chunk ON blobs (chunk_index);'
    ]

    _db_transaction_factory = CockroachDBTransaction
    _vacuum = _vacuum_task = None
    _isolation_level = 'snapshot'

    def __init__(self, *args, **kwargs):
        transaction_strategy = kwargs.get('transaction_strategy', 'novote')
        self._isolation_level = kwargs.get('isolation_level', 'snapshot').lower()
        if (self._isolation_level == 'serializable' and
                transaction_strategy not in ('none', 'tidonly', 'novote', 'lock')):
            logger.warning(f'Unsupported transaction strategy specified for '
                           f'cockroachdb SERIALIZABLE isolation level'
                           f'({transaction_strategy}). Forcing to `novote` strategy')
            transaction_strategy = 'novote'
        kwargs['transaction_strategy'] = transaction_strategy
        super().__init__(*args, **kwargs)

    async def initialize_tid_statements(self):
        self._stmt_next_tid = await self._read_conn.prepare(NEXT_TID)
        self._stmt_max_tid = await self._read_conn.prepare(MAX_TID)

    async def open(self):
        conn = await super().open()
        if self._transaction_strategy in ('none', 'tidonly', 'lock'):
            # if a strategy is used that is not a db transaction we can't
            # set the isolation level along with the transaction start
            await conn.execute(
                'SET DEFAULT_TRANSACTION_ISOLATION TO ' + self._isolation_level)
        return conn

    async def initialize(self, loop=None):
        await super().initialize(loop=loop)
        # we need snapshot isolation to allow us to work together with
        # other transactions nicely and prevent deadlocks
        await self._read_conn.execute('SET DEFAULT_TRANSACTION_ISOLATION TO SNAPSHOT')
        self._vacuum = CockroachVacuum(self, loop)
        self._vacuum_task = asyncio.Task(self._vacuum.initialize(), loop=loop)

        def vacuum_done(task):
            if self._vacuum._closed:
                # if it's closed, we know this is expected
                return
            logger.warning('Vacuum cockroach task closed. This should not happen. '
                           'No database vacuuming will be done here anymore.')

        self._vacuum_task.add_done_callback(vacuum_done)

    async def finalize(self):
        await self._vacuum.finalize()
        self._vacuum_task.cancel()
        await super().finalize()

    async def store(self, oid, old_serial, writer, obj, txn):
        assert oid is not None

        p = writer.serialize()  # This calls __getstate__ of obj
        if len(p) >= self._large_record_size:
            self._log.warning("Too long object %d" % (obj.__class__, len(p)))
        part = writer.part
        if part is None:
            part = 0

        update = False
        statement_sql = NAIVE_UPSERT
        if not obj.__new_marker__ and obj._p_serial is not None:
            # we should be confident this is an object update
            statement_sql = UPDATE
            update = True

        async with txn._lock:
            smt = await txn._db_conn.prepare(statement_sql)
            try:
                result = await smt.fetch(
                    oid,                 # The OID of the object
                    txn._tid,            # Our TID
                    len(p),              # Len of the object
                    part,                # Partition indicator
                    writer.resource,     # Is a resource ?
                    writer.of,           # It belogs to a main
                    old_serial,          # Old serial
                    writer.parent_id,    # Parent OID
                    writer.id,           # Traversal ID
                    writer.type,         # Guillotina type
                    p                    # Pickle state)
                )
            except asyncpg.exceptions._base.InterfaceError as ex:
                if 'another operation is in progress' in ex.args[0]:
                    raise ConflictError(
                        'asyncpg error, another operation in progress.')
                raise
            if update and len(result) != 1:
                # raise tid conflict error
                raise TIDConflictError(
                    'Mismatch of tid of object being updated. This is likely '
                    'caused by a cache invalidation race condition and should '
                    'be an edge case. This should resolve on request retry.')
        obj._p_estimated_size = len(p)

    async def _txn_oid_commit_hook(self, status, oid):
        await self._vacuum.add_to_queue(oid)

    async def delete(self, txn, oid):
        # no cascade support, so we push to vacuum
        async with txn._lock:
            await txn._db_conn.execute(pg.DELETE_FROM_OBJECTS, oid)
            await txn._db_conn.execute(DELETE_FROM_BLOBS, oid)
        txn.add_after_commit_hook(self._txn_oid_commit_hook, [oid])

    async def commit(self, transaction):
        if transaction._db_txn is not None:
            async with transaction._lock:
                try:
                    await transaction._db_txn.commit()
                except asyncpg.exceptions.SerializationError as ex:
                    if 'restart transaction' in ex.args[0]:
                        raise ConflictError(ex.args[0])
        elif self._transaction_strategy not in ('none', 'tidonly'):
            logger.warning('Do not have db transaction to commit')

        return transaction._tid
