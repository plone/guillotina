from asyncio import shield
from guillotina.db.interfaces import IStorage
from guillotina.db.storages.base import BaseStorage
from guillotina.db.storages.utils import get_table_definition
from guillotina.exceptions import ConflictError
from guillotina.exceptions import TIDConflictError
from zope.interface import implementer

import asyncio
import asyncpg
import logging
import ujson


log = logging.getLogger("guillotina.storage")


# we can not use FOR UPDATE or FOR SHARE unfortunately because
# it can cause deadlocks on the database--we need to resolve them ourselves
GET_OID = """
    SELECT zoid, tid, state_size, resource, of, parent_id, id, type, state
    FROM objects
    WHERE zoid = $1::varchar(32)
    """

GET_CHILDREN_KEYS = """
    SELECT id
    FROM objects
    WHERE parent_id = $1::varchar(32)
    """

GET_ANNOTATIONS_KEYS = """
    SELECT id
    FROM objects
    WHERE of = $1::varchar(32)
    """

GET_CHILD = """
    SELECT zoid, tid, state_size, resource, type, state, id
    FROM objects
    WHERE parent_id = $1::varchar(32) AND id = $2::text
    """

EXIST_CHILD = """
    SELECT zoid
    FROM objects
    WHERE parent_id = $1::varchar(32) AND id = $2::text
    """


HAS_OBJECT = """
    SELECT zoid
    FROM objects
    WHERE zoid = $1::varchar(32)
    """


GET_ANNOTATION = """
    SELECT zoid, tid, state_size, resource, type, state, id
    FROM objects
    WHERE of = $1::varchar(32) AND id = $2::text
    """


def _wrap_return_count(txt):
    return """WITH rows AS (
{}
    RETURNING 1
)
SELECT count(*) FROM rows""".format(txt)


# upsert without checking matching tids on updated object
NAIVE_UPSERT = """
INSERT INTO objects
(zoid, tid, state_size, part, resource, of, otid, parent_id, id, type, json, state)
VALUES ($1::varchar(32), $2::int, $3::int, $4::int, $5::boolean, $6::varchar(32), $7::int,
        $8::varchar(32), $9::text, $10::text, $11::json, $12::bytea)
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
    json = EXCLUDED.json,
    state = EXCLUDED.state"""
UPSERT = _wrap_return_count(NAIVE_UPSERT + """
    WHERE
        tid = EXCLUDED.otid""")
NAIVE_UPSERT = _wrap_return_count(NAIVE_UPSERT)


# update without checking matching tids on updated object
NAIVE_UPDATE = """
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
    json = $11::json,
    state = $12::bytea
WHERE
    zoid = $1::varchar(32)"""
UPDATE = _wrap_return_count(NAIVE_UPDATE + """ AND tid = $7::int""")
NAIVE_UPDATE = _wrap_return_count(NAIVE_UPDATE)


NEXT_TID = "SELECT nextval('tid_sequence');"
MAX_TID = "SELECT last_value FROM tid_sequence;"


NUM_CHILDREN = "SELECT count(*) FROM objects WHERE parent_id = $1::varchar(32)"


NUM_ROWS = "SELECT count(*) FROM objects"


NUM_RESOURCES = "SELECT count(*) FROM objects WHERE resource is TRUE"

NUM_RESOURCES_BY_TYPE = "SELECT count(*) FROM objects WHERE type=$1::TEXT"

RESOURCES_BY_TYPE = """
    SELECT zoid, tid, state_size, resource, type, state, id
    FROM objects
    WHERE type=$1::TEXT
    ORDER BY zoid
    LIMIT $2::int
    OFFSET $3::int
    """


GET_CHILDREN = """
    SELECT zoid, tid, state_size, resource, type, state, id
    FROM objects
    WHERE parent_id = $1::VARCHAR(32)
    """


DELETE_FROM_OBJECTS = """
    DELETE FROM objects WHERE zoid = $1::varchar(32);
"""


INSERT_BLOB_CHUNK = """
    INSERT INTO blobs
    (bid, zoid, chunk_index, data)
    VALUES ($1::VARCHAR(32), $2::VARCHAR(32), $3::INT, $4::BYTEA)
"""


READ_BLOB_CHUNKS = """
    SELECT * from blobs
    WHERE bid = $1::VARCHAR(32)
    ORDER BY chunk_index
"""

READ_BLOB_CHUNK = """
    SELECT * from blobs
    WHERE bid = $1::VARCHAR(32)
    AND chunk_index = $2::int
"""


DELETE_BLOB = """
    DELETE FROM blobs WHERE bid = $1::VARCHAR(32);
"""


TXN_CONFLICTS = """
    SELECT zoid, tid, state_size, resource, type, id
    FROM objects
    WHERE tid > $1
    """


TXN_CONFLICTS_FULL = """
    SELECT zoid, tid, state_size, resource, type, state, id
    FROM objects
    WHERE tid > $1
    """

BATCHED_GET_CHILDREN_KEYS = """
    SELECT id
    FROM objects
    WHERE parent_id = $1::varchar(32)
    ORDER BY zoid
    LIMIT $2::int
    OFFSET $3::int
    """


@implementer(IStorage)
class PostgresqlStorage(BaseStorage):
    """Storage to a relational database, based on invalidation polling"""

    _dsn = None
    _partition_class = None
    _pool_size = None
    _pool = None
    _large_record_size = 1 << 24

    _object_schema = {
        'zoid': 'VARCHAR(32) NOT NULL PRIMARY KEY',
        'tid': 'BIGINT NOT NULL',
        'state_size': 'BIGINT NOT NULL',
        'part': 'BIGINT NOT NULL',
        'resource': 'BOOLEAN NOT NULL',
        'of': 'VARCHAR(32) REFERENCES objects ON DELETE CASCADE',
        'otid': 'BIGINT',
        'parent_id': 'VARCHAR(32) REFERENCES objects ON DELETE CASCADE',  # parent oid
        'id': 'TEXT',
        'type': 'TEXT NOT NULL',
        'json': 'JSONB',
        'state': 'BYTEA'
    }

    _blob_schema = {
        'bid': 'VARCHAR(32) NOT NULL',
        'zoid': 'VARCHAR(32) NOT NULL REFERENCES objects ON DELETE CASCADE',
        'chunk_index': 'INT NOT NULL',
        'data': 'BYTEA'
    }

    _initialize_statements = [
        'CREATE INDEX IF NOT EXISTS object_tid ON objects (tid);',
        'CREATE INDEX IF NOT EXISTS object_of ON objects (of);',
        'CREATE INDEX IF NOT EXISTS object_part ON objects (part);',
        'CREATE INDEX IF NOT EXISTS object_parent ON objects (parent_id);',
        'CREATE INDEX IF NOT EXISTS object_id ON objects (id);',
        'CREATE INDEX IF NOT EXISTS blob_bid ON blobs (bid);',
        'CREATE INDEX IF NOT EXISTS blob_zoid ON blobs (zoid);',
        'CREATE INDEX IF NOT EXISTS blob_chunk ON blobs (chunk_index);',
        'CREATE SEQUENCE IF NOT EXISTS tid_sequence;'
    ]

    def __init__(self, dsn=None, partition=None, read_only=False, name=None,
                 pool_size=12, transaction_strategy='resolve',
                 conn_acquire_timeout=20, cache_strategy='dummy', **options):
        super(PostgresqlStorage, self).__init__(
            read_only, transaction_strategy=transaction_strategy,
            cache_strategy=cache_strategy)
        self._dsn = dsn
        self._pool_size = pool_size
        self._partition_class = partition
        self._read_only = read_only
        self.__name__ = name
        self._read_conn = None
        self._lock = asyncio.Lock()
        self._conn_acquire_timeout = conn_acquire_timeout
        self._options = options

    async def finalize(self):
        await self._pool.release(self._read_conn)
        await self._pool.close()

    async def create(self):
        # Check DB
        log.info('Creating initial database objects')
        statements = [
            get_table_definition('objects', self._object_schema),
            get_table_definition('blobs', self._blob_schema,
                                 primary_keys=('bid', 'zoid', 'chunk_index'))
        ]
        statements.extend(self._initialize_statements)

        for statement in statements:
            await self._read_conn.execute(statement)

        await self.initialize_tid_statements()
        # migrate old transaction table scheme over
        try:
            old_tid = await self._read_conn.fetchval('SELECT max(tid) from transaction')
            current_tid = await self.get_current_tid(None)
            if old_tid > current_tid:
                await self._read_conn.execute(
                    'ALTER SEQUENCE tid_sequence RESTART WITH ' + str(old_tid + 1))
        except asyncpg.exceptions.UndefinedTableError:
            # no need to upgrade
            pass

    async def initialize(self, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            max_size=self._pool_size,
            min_size=2,
            loop=loop)

        # shared read connection on all transactions
        self._read_conn = await self.open()
        try:
            await self.initialize_tid_statements()
        except asyncpg.exceptions.UndefinedTableError:
            await self.create()
            await self.initialize_tid_statements()

    async def initialize_tid_statements(self):
        self._stmt_next_tid = await self._read_conn.prepare(NEXT_TID)
        self._stmt_max_tid = await self._read_conn.prepare(MAX_TID)

    async def remove(self):
        """Reset the tables"""
        async with self._pool.acquire() as conn:
            await conn.execute("DROP TABLE IF EXISTS blobs;")
            await conn.execute("DROP TABLE IF EXISTS objects;")

    async def open(self):
        conn = await self._pool.acquire(timeout=self._conn_acquire_timeout)
        return conn

    async def close(self, con):
        try:
            await shield(self._pool.release(con))
        except asyncio.CancelledError:
            pass

    async def load(self, txn, oid):
        async with txn._lock:
            smt = await txn._db_conn.prepare(GET_OID)
            objects = await smt.fetchrow(oid)
        if objects is None:
            raise KeyError(oid)
        return objects

    async def store(self, oid, old_serial, writer, obj, txn):
        assert oid is not None

        p = writer.serialize()  # This calls __getstate__ of obj
        if len(p) >= self._large_record_size:
            self._log.warning("Too long object %d" % (obj.__class__, len(p)))
        json_dict = await writer.get_json()
        json = ujson.dumps(json_dict)
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
                    json,                # JSON catalog
                    p                    # Pickle state)
                )
            except asyncpg.exceptions.ForeignKeyViolationError:
                txn.deleted[obj._p_oid] = obj
                raise TIDConflictError(
                    'Bad value inserting into database that could be caused '
                    'by a bad cache value. This should resolve on request retry.')
            except asyncpg.exceptions._base.InterfaceError as ex:
                if 'another operation is in progress' in ex.args[0]:
                    raise ConflictError(
                        'asyncpg error, another operation in progress.')
                raise
            except asyncpg.exceptions.DeadlockDetectedError:
                raise ConflictError(
                    'Deadlock detected.')
            if len(result) != 1 or result[0]['count'] != 1:
                if update:
                    # raise tid conflict error
                    raise TIDConflictError(
                        'Mismatch of tid of object being updated. This is likely '
                        'caused by a cache invalidation race condition and should '
                        'be an edge case. This should resolve on request retry.')
                else:
                    self._log.error('Incorrect response count from database update. '
                                    'This should not happen. tid: {}'.format(txn._tid))
        obj._p_estimated_size = len(p)

    async def delete(self, txn, oid):
        async with txn._lock:
            await txn._db_conn.execute(DELETE_FROM_OBJECTS, oid)

    async def get_next_tid(self, txn):
        async with self._lock:
            # we do not use transaction lock here but a storage lock because
            # a storage object has a shard conn for reads
            return await self._stmt_next_tid.fetchval()

    async def get_current_tid(self, txn):
        async with self._lock:
            # again, use storage lock here instead of trns lock
            return await self._stmt_max_tid.fetchval()

    def _db_transaction_factory(self, txn):
        # make sure asycpg knows this is a new transaction
        if txn._db_conn._con is not None:
            txn._db_conn._con._top_xact = None
        return txn._db_conn.transaction(readonly=txn._manager._storage._read_only)

    async def start_transaction(self, txn, retries=0):
        error = None
        async with txn._lock:
            txn._db_txn = self._db_transaction_factory(txn)
            try:
                await txn._db_txn.start()
                return
            except asyncpg.exceptions._base.InterfaceError as ex:
                error = ex

        if error is not None:
            if retries > 2:
                raise error

            if ('manually started transaction' in error.args[0] or
                    'connection is closed' in error.args[0]):
                if 'manually started transaction' in error.args[0]:
                    try:
                        # thinks we're manually in txn, manually rollback and try again...
                        await txn._db_conn.execute('ROLLBACK;')
                    except asyncpg.exceptions._base.InterfaceError:
                        # we're okay with this error here...
                        pass
                await self.close(txn._db_conn)
                txn._db_conn = await self.open()
                return await self.start_transaction(txn, retries + 1)

    async def get_conflicts(self, txn, full=False):
        async with self._lock:
            # use storage lock instead of transaction lock
            if full:
                return await self._read_conn.fetch(TXN_CONFLICTS_FULL, txn._tid)
            else:
                return await self._read_conn.fetch(TXN_CONFLICTS, txn._tid)

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
    async def get_page_of_keys(self, txn, oid, page=1, page_size=1000):
        conn = txn._db_conn
        smt = await conn.prepare(BATCHED_GET_CHILDREN_KEYS)
        keys = []
        for record in await smt.fetch(oid, page_size, (page - 1) * page_size):
            keys.append(record['id'])
        return keys

    async def keys(self, txn, oid):
        async with txn._lock:
            smt = await txn._db_conn.prepare(GET_CHILDREN_KEYS)
            result = await smt.fetch(oid)
        return result

    async def get_child(self, txn, parent_oid, id):
        async with txn._lock:
            smt = await txn._db_conn.prepare(GET_CHILD)
            result = await smt.fetchrow(parent_oid, id)
        return result

    async def has_key(self, txn, parent_oid, id):
        async with txn._lock:
            smt = await txn._db_conn.prepare(EXIST_CHILD)
            result = await smt.fetchrow(parent_oid, id)
        if result is None:
            return False
        else:
            return True

    async def len(self, txn, oid):
        async with txn._lock:
            smt = await txn._db_conn.prepare(NUM_CHILDREN)
            result = await smt.fetchval(oid)
        return result

    async def items(self, txn, oid):
        async with txn._lock:
            smt = await txn._db_conn.prepare(GET_CHILDREN)
        async for record in smt.cursor(oid):
            # locks are dangerous in cursors since comsuming code might do
            # sub-queries and they you end up with a deadlock
            yield record

    async def get_annotation(self, txn, oid, id):
        async with txn._lock:
            smt = await txn._db_conn.prepare(GET_ANNOTATION)
            result = await smt.fetchrow(oid, id)
        return result

    async def get_annotation_keys(self, txn, oid):
        async with txn._lock:
            smt = await txn._db_conn.prepare(GET_ANNOTATIONS_KEYS)
            result = await smt.fetch(oid)
        return result

    async def write_blob_chunk(self, txn, bid, oid, chunk_index, data):
        async with txn._lock:
            smt = await txn._db_conn.prepare(HAS_OBJECT)
            result = await smt.fetchrow(oid)
        if result is None:
            # check if we have a referenced ob, could be new and not in db yet.
            # if so, create a stub for it here...
            async with txn._lock:
                await txn._db_conn.execute('''INSERT INTO objects
                    (zoid, tid, state_size, part, resource, type)
                    VALUES ($1::varchar(32), -1, 0, 0, TRUE, 'stub')''', oid)
        async with txn._lock:
            return await txn._db_conn.execute(
                INSERT_BLOB_CHUNK, bid, oid, chunk_index, data)

    async def read_blob_chunk(self, txn, bid, chunk=0):
        async with txn._lock:
            smt = await txn._db_conn.prepare(READ_BLOB_CHUNK)
            return await smt.fetchrow(bid, chunk)

    async def read_blob_chunks(self, txn, bid):
        async with txn._lock:
            smt = await txn._db_conn.prepare(READ_BLOB_CHUNKS)
        async for record in smt.cursor(bid):
            # locks are dangerous in cursors since comsuming code might do
            # sub-queries and they you end up with a deadlock
            yield record

    async def del_blob(self, txn, bid):
        async with txn._lock:
            await txn._db_conn.execute(DELETE_BLOB, bid)

    async def get_total_number_of_objects(self, txn):
        async with txn._lock:
            smt = await txn._db_conn.prepare(NUM_ROWS)
            result = await smt.fetchval()
        return result

    async def get_total_number_of_resources(self, txn):
        async with txn._lock:
            smt = await txn._db_conn.prepare(NUM_RESOURCES)
            result = await smt.fetchval()
        return result

    async def get_total_resources_of_type(self, txn, type_):
        async with txn._lock:
            smt = await txn._db_conn.prepare(NUM_RESOURCES_BY_TYPE)
            result = await smt.fetchval(type_)
        return result

    # Massive treatment without security
    async def _get_page_resources_of_type(self, txn, type_, page, page_size):
        conn = txn._db_conn
        async with txn._lock:
            smt = await conn.prepare(RESOURCES_BY_TYPE)
        keys = []
        for record in await smt.fetch(type_, page_size, (page - 1) * page_size):  # noqa
            keys.append(record)
        return keys
