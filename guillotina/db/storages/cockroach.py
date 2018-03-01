from guillotina import glogging
from guillotina.db.storages import pg
from guillotina.exceptions import ConflictError
from guillotina.exceptions import RestartCommit
from guillotina.exceptions import TIDConflictError

import asyncpg


logger = glogging.getLogger('guillotina')

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
    state = EXCLUDED.state
RETURNING NOTHING"""


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

DELETE_FROM_BLOBS = """DELETE FROM blobs WHERE zoid = $1::varchar(32) RETURNING NOTHING;"""

DELETE_BY_PARENT_OID = '''DELETE FROM objects
WHERE parent_id = $1::varchar(32)
RETURNING NOTHING;'''

BATCHED_GET_CHILDREN_OIDS = """
SELECT zoid FROM objects
WHERE parent_id = $1::varchar(32)
ORDER BY zoid
LIMIT $2::int
OFFSET $3::int;"""

DELETE_OBJECT = f"""
DELETE FROM objects
WHERE zoid = $1::varchar(32)
RETURNING NOTHING;
"""


async def iterate_children(conn, parent_oid, page_size=1000):
    smt = await conn.prepare(BATCHED_GET_CHILDREN_OIDS)
    page = 1
    results = await smt.fetch(parent_oid, page_size, (page - 1) * page_size)
    while len(results) > 0:
        for record in results:
            yield record['zoid']
        page += 1
        results = await smt.fetch(parent_oid, page_size, (page - 1) * page_size)


class CockroachVacuum(pg.PGVacuum):

    async def vacuum_children(self, conn, parent_oid):
        async for child_oid in iterate_children(conn, parent_oid):
            await self.vacuum_children(conn, child_oid)
        await conn.execute(DELETE_BY_PARENT_OID, parent_oid)
        await conn.execute(DELETE_FROM_BLOBS, parent_oid)

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
            await self._storage.close(conn)


class CockroachDBTransaction:
    '''
    Custom transaction object to work with cockroachdb so we can...
    1. restart commits when cockroach throws a 40001 error
    2. retry transctions with custom priorities
    '''

    commit_statement = '''RELEASE SAVEPOINT cockroach_restart;
COMMIT;'''

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
        await self._conn.execute(f'''BEGIN PRIORITY {self._priority};
SAVEPOINT cockroach_restart;''')
        self._status = 'started'

    async def commit(self):
        assert self._status in ('started',)
        await self._conn.execute(self.commit_statement)
        self._status = 'committed'

    async def restart(self):
        await self._conn.execute('ROLLBACK TO SAVEPOINT COCKROACH_RESTART')

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
            - cockroachdb 2.0 has it but is alpha!
        - no sequence support
            - use serial construct of unique_rowid() instead
        - referencial integrity support
            - latest cockroachdb has it; however, without ON DELETE CASCADE,
              it is not worth implementing yet like the postgresql driver
    Once cockroachdb 2.0 is stable...
        - we can change this cockroach driver to work almost the exact same
          way as postgresql driver with on delete cascade support
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
    _vacuum_class = CockroachVacuum

    def __init__(self, *args, **kwargs):
        transaction_strategy = kwargs.get('transaction_strategy', 'dbresolve_readcommitted')
        if transaction_strategy not in (
                'none', 'tidonly', 'dbresolve', 'dbresolve_readcommitted'):
            logger.warning(f'Unsupported transaction strategy specified for '
                           f'cockroachdb({transaction_strategy}). '
                           f'Forcing to `dbresolve_readcommitted` strategy')
            transaction_strategy = 'dbresolve_readcommitted'
        kwargs['transaction_strategy'] = transaction_strategy
        super().__init__(*args, **kwargs)

    async def initialize_tid_statements(self):
        self._stmt_next_tid = await self._read_conn.prepare(NEXT_TID)

    async def get_current_tid(self, txn):
        raise Exception("cockroach does not support voting")

    async def store(self, oid, old_serial, writer, obj, txn):
        assert oid is not None

        pickled = writer.serialize()  # This calls __getstate__ of obj
        if len(pickled) >= self._large_record_size:
            logger.warning(f"Large object {obj.__class__}: {len(pickled)}")
        part = writer.part
        if part is None:
            part = 0

        statement_sql = NAIVE_UPSERT
        update = False
        if not obj.__new_marker__ and obj._p_serial is not None:
            # we should be confident this is an object update
            statement_sql = UPDATE
            update = True

        conn = await txn.get_connection()
        async with txn._lock:
            try:
                result = await conn.fetch(
                    statement_sql,
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
                    pickled              # Pickle state)
                )
            except asyncpg.exceptions._base.InterfaceError as ex:
                if 'another operation is in progress' in ex.args[0]:
                    raise ConflictError(
                        f'asyncpg error, another operation in progress.',
                        oid, txn, old_serial, writer)
                raise
            if update and len(result) != 1:
                # raise tid conflict error
                raise TIDConflictError(
                    f'Mismatch of tid of object being updated. This is likely '
                    f'caused by a cache invalidation race condition and should '
                    f'be an edge case. This should resolve on request retry.',
                    oid, txn, old_serial, writer)
        await txn._cache.store_object(obj, pickled)

    async def delete(self, txn, oid):
        # no cascade support, so we push to vacuum
        async with txn._lock:
            conn = await txn.get_connection()
            await conn.execute(DELETE_OBJECT, oid)
            await conn.execute(DELETE_FROM_BLOBS, oid)
        txn.add_after_commit_hook(self._txn_oid_commit_hook, oid)

    async def commit(self, transaction):
        if transaction._db_txn is not None:
            async with transaction._lock:
                try:
                    await transaction._db_txn.commit()
                except asyncpg.exceptions.SerializationError as ex:
                    if ex.sqlstate == '40001':
                        raise RestartCommit(ex.args[0])
        elif self._transaction_strategy not in ('none', 'tidonly'):
            logger.warning('Do not have db transaction to commit')

        return transaction._tid

    # Cockroach cant use at version 1.0.3 row count (no fetch)
    async def get_one_row(self, txn, sql, *args, prepare=False):
        # Helper function to provide easy adaptation to cockroach
        conn = await txn.get_connection()
        try:
            # Helper function to provide easy adaptation to cockroach
            if prepare:
                # latest version of asyncpg has prepare bypassing statement cache
                smt = await conn.prepare(sql)
                result = await smt.fetch(*args)
            else:
                result = await conn.fetch(sql, *args)
        except asyncpg.exceptions.SerializationError as ex:
            if ex.sqlstate == '40001':
                # these are not handled with the ROLLBACK TO SAVEPOINT COCKROACH_RESTART
                # logic unfortunately; however, it does give us a chance to handle
                # it like a restart with higher priority
                raise ConflictError(ex.args[0])
        return result[0] if len(result) > 0 else None
