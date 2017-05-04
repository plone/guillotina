from asyncio import shield
from guillotina.db.interfaces import IStorage
from guillotina.db.storages.base import BaseStorage
from guillotina.db.storages.utils import get_table_definition
from zope.interface import implementer

import asyncio
import asyncpg
import logging
import ujson


log = logging.getLogger("guillotina.storage")


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

MAX_TID = """
    SELECT max(tid) FROM objects
    """


INSERT = """
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
        state = EXCLUDED.state;
    """


# not used right now but here in case we want to try specifically doing updates
# instead of insert + on conflict
UPDATE = """
    UPDATE objects
    SET (
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
        state = $12::bytea)
    WHERE zoid = $1::varchar(32)
    """


NEXT_TID = """UPDATE transaction
SET tid = tid + 1
WHERE id = 1
RETURNING tid;"""
CURRENT_TID = "SELECT tid from transaction"


NUM_CHILDREN = "SELECT count(*) FROM objects WHERE parent_id = $1::varchar(32)"


NUM_ROWS = "SELECT count(*) FROM objects"


NUM_RESOURCES = "SELECT count(*) FROM objects WHERE resource is TRUE"


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
    SELECT zoid, tid, state_size, resource, type, state, id
    FROM objects
    WHERE tid > $1
    """

TIMEOUT_TO_ACQUIRE = 20


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

    # will be a one-row table to hold current transaction id
    # why:
    #   - 1: you can lock it, you can not lock a sequence
    #   - 2: compat with cockroach db
    _transaction_schema = {
        'id': 'INT NOT NULL PRIMARY KEY',
        'tid': 'BIGINT'
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
        'CREATE INDEX IF NOT EXISTS transaction_tid ON transaction (tid);',
        'INSERT INTO transaction (id, tid) VALUES (1, 1) ON CONFLICT (id) DO NOTHING'
    ]

    def __init__(self, dsn=None, partition=None, read_only=False, name=None,
                 pool_size=10, transaction_strategy='resolve', **options):
        super(PostgresqlStorage, self).__init__(
            read_only, transaction_strategy=transaction_strategy)
        self._dsn = dsn
        self._pool_size = pool_size
        self._partition_class = partition
        self._read_only = read_only
        self.__name__ = name
        self._trns_conn = None
        self._lock = asyncio.Lock()
        self._options = options

    async def finalize(self):
        await self._pool.release(self._trns_conn)
        await self._pool.close()

    async def initialize(self, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            max_size=self._pool_size,
            min_size=2,
            loop=loop)

        # Check DB
        statements = [
            get_table_definition('objects', self._object_schema),
            get_table_definition('transaction', self._transaction_schema),
            get_table_definition('blobs', self._blob_schema,
                                 primary_keys=('bid', 'zoid', 'chunk_index'))
        ]
        statements.extend(self._initialize_statements)

        async with self._pool.acquire() as conn:
            for statement in statements:
                await conn.execute(statement)

        # shared read connection on all transactions
        self._trns_conn = await self.open()
        await self.initialize_tid_statements()

        # migrate old tid scheme over
        try:
            old_tid = await self._trns_conn.fetchval('SELECT last_value from tid_seq')
            current_tid = await self.get_current_tid(None)
            if old_tid > current_tid:
                await self._trns_conn.fetchval('UPDATE transaction SET tid = $1::int', old_tid)
        except asyncpg.exceptions.UndefinedTableError:
            # no need to upgrade
            pass

    async def initialize_tid_statements(self):
        self._stmt_next_tid = await self._trns_conn.prepare(NEXT_TID)
        self._stmt_current_tid = await self._trns_conn.prepare(CURRENT_TID)

    async def remove(self):
        """Reset the tables"""
        async with self._pool.acquire() as conn:
            await conn.execute("DROP TABLE IF EXISTS blobs;")
            await conn.execute("DROP TABLE IF EXISTS objects;")

    async def open(self):
        conn = await self._pool.acquire(timeout=TIMEOUT_TO_ACQUIRE)
        return conn

    async def close(self, con):
        try:
            await shield(self._pool.release(con))
        except asyncio.CancelledError:
            pass

    async def _get_prepared_statement(self, txn, name, statement, retries=0):
        '''
        lazy load prepared statements so we don't do unncessary
        calls to pg...
        '''
        name = '_smt_' + name
        if not hasattr(txn, name):
            # setattr(txn, name, await txn._db_conn.prepare(statement))
            try:
                setattr(txn, name, await txn._db_conn.prepare(statement))
            except asyncpg.exceptions.InterfaceError as exc:
                if retries < 5:
                    asyncio.sleep(0.01 * retries)
                    return await self._get_prepared_statement(
                        txn, name, statement, retries + 1)
                else:
                    raise
        return getattr(txn, name)

    async def last_transaction(self, txn):
        smt = await self._get_prepared_statement(txn, 'max_tid', MAX_TID)
        value = await smt.fetchval()
        return 0 if value is None else value

    async def load(self, txn, oid):
        int_oid = oid
        smt = await self._get_prepared_statement(txn, 'get_oid', GET_OID)
        objects = await smt.fetchrow(int_oid)
        if objects is None:
            raise KeyError(oid)
        return objects

    async def store(self, oid, old_serial, writer, obj, txn):
        assert oid is not None

        smt = await self._get_prepared_statement(txn, 'insert', INSERT)

        p = writer.serialize()  # This calls __getstate__ of obj
        if len(p) >= self._large_record_size:
            self._log.warn("Too long object %d" % (obj.__class__, len(p)))
        json_dict = await writer.get_json()
        json = ujson.dumps(json_dict)
        part = writer.part
        if part is None:
            part = 0
        # (zoid, tid, state_size, part, main, parent_id, type, json, state)
        await smt.fetchval(
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
            p                    # Pickle state
        )
        obj._p_estimated_size = len(p)
        return txn._tid, len(p)

    async def delete(self, txn, oid):
        await txn._db_conn.execute(DELETE_FROM_OBJECTS, oid)

    async def get_next_tid(self, txn):
        async with self._lock:
            return await self._stmt_next_tid.fetchval()

    async def start_transaction(self, txn):
        txn._db_txn = txn._db_conn.transaction(readonly=self._read_only)
        await txn._db_txn.start()

    async def get_current_tid(self, txn):
        async with self._lock:
            return await self._stmt_current_tid.fetchval()

    async def get_conflicts(self, txn):
        return await self._trns_conn.fetch(TXN_CONFLICTS, txn._tid)

    async def commit(self, transaction):
        if transaction._db_txn is not None:
            await transaction._db_txn.commit()
        else:
            log.warn('Do not have db transaction to commit')
        return transaction._tid

    async def abort(self, transaction):
        if transaction._db_txn is not None:
            await transaction._db_txn.rollback()
        else:
            log.warn('Do not have db transaction to rollback')

    # Introspection

    async def keys(self, txn, oid):
        smt = await self._get_prepared_statement(txn, 'get_sons_keys', GET_CHILDREN_KEYS)
        result = await smt.fetch(oid)
        return result

    async def get_child(self, txn, parent_oid, id):
        smt = await self._get_prepared_statement(txn, 'get_child', GET_CHILD)
        result = await smt.fetchrow(parent_oid, id)
        return result

    async def has_key(self, txn, parent_oid, id):
        smt = await self._get_prepared_statement(txn, 'exist_child', EXIST_CHILD)
        result = await smt.fetchrow(parent_oid, id)
        if result is None:
            return False
        else:
            return True

    async def len(self, txn, oid):
        smt = await self._get_prepared_statement(txn, 'num_childs', NUM_CHILDREN)
        result = await smt.fetchval(oid)
        return result

    async def items(self, txn, oid):
        smt = await self._get_prepared_statement(txn, 'get_childs', GET_CHILDREN)
        async for record in smt.cursor(oid):
            yield record

    async def get_annotation(self, txn, oid, id):
        smt = await self._get_prepared_statement(txn, 'get_annotation', GET_ANNOTATION)
        result = await smt.fetchrow(oid, id)
        return result

    async def get_annotation_keys(self, txn, oid):
        smt = await self._get_prepared_statement(
            txn, 'get_annotations_keys', GET_ANNOTATIONS_KEYS)
        result = await smt.fetch(oid)
        return result

    async def write_blob_chunk(self, txn, bid, oid, chunk_index, data):
        smt = await self._get_prepared_statement(txn, 'has_ob', HAS_OBJECT)
        result = await smt.fetchrow(oid)
        if result is None:
            # check if we have a referenced ob, could be new and not in db yet.
            # if so, create a stub for it here...
            await txn._db_conn.execute('''INSERT INTO objects
                (zoid, tid, state_size, part, resource, type)
                VALUES ($1::varchar(32), -1, 0, 0, TRUE, 'stub')''', oid)
        return await txn._db_conn.execute(
            INSERT_BLOB_CHUNK, bid, oid, chunk_index, data)

    async def read_blob_chunk(self, txn, bid, chunk=0):
        smt = await self._get_prepared_statement(txn, 'read_blob_chunk', READ_BLOB_CHUNK)
        return await smt.fetchrow(bid, chunk)

    async def read_blob_chunks(self, txn, bid):
        smt = await self._get_prepared_statement(txn, 'read_blob_chunks', READ_BLOB_CHUNKS)
        async for record in smt.cursor(bid):
            yield record

    async def del_blob(self, txn, bid):
        await txn._db_conn.execute(DELETE_BLOB, bid)

    async def get_total_number_of_objects(self, txn):
        smt = await self._get_prepared_statement(txn, 'num_rows', NUM_ROWS)
        result = await smt.fetchval()
        return result

    async def get_total_number_of_resources(self, txn):
        smt = await self._get_prepared_statement(txn, 'num_resources', NUM_RESOURCES)
        result = await smt.fetchval()
        return result
