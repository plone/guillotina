from guillotina.db.storages import pg
from guillotina.exceptions import ConflictError
from guillotina.exceptions import TIDConflictError
import asyncpg, sys


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
MAX_TID = "SELECT MAX(tid) from objects;"


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
    '''

    _object_schema = pg.PostgresqlStorage._object_schema.copy()
    del _object_schema['json']  # no json db support
    _object_schema.update({
        'of': 'VARCHAR(32) REFERENCES objects',
        'parent_id': 'VARCHAR(32) REFERENCES objects',  # parent oid
    })

    _blob_schema = pg.PostgresqlStorage._blob_schema.copy()
    _blob_schema.update({
        'zoid': 'VARCHAR(32) NOT NULL REFERENCES objects',
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

    _max_tid = 0

    async def initialize_tid_statements(self):
        self._stmt_next_tid = await self._read_conn.prepare(NEXT_TID)
        self._stmt_max_tid = await self._read_conn.prepare(MAX_TID)
        if hasattr(sys, '_db_tests'):
            self.get_current_tid = self._test_get_current_tid

    async def _test_get_current_tid(self, txn):
        return self._max_tid

    async def store(self, oid, old_serial, writer, obj, txn):
        assert oid is not None

        p = writer.serialize()  # This calls __getstate__ of obj
        if len(p) >= self._large_record_size:
            self._log.warn("Too long object %d" % (obj.__class__, len(p)))
        part = writer.part
        if part is None:
            part = 0

        update = False
        statement_sql = NAIVE_UPSERT
        if not obj.__new_marker__ and obj._p_serial is not None:
            # we should be confident this is an object update
            statement_sql = UPDATE
            update = True

        if hasattr(sys, '_db_tests') and txn._tid > self._max_tid:
            self._max_tid = txn._tid

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
            if update and len(result) != 1:
                # raise tid conflict error
                raise TIDConflictError(
                    'Mismatch of tid of object being updated. This is likely '
                    'caused by a cache invalidation race condition and should '
                    'be an edge case. This should resolve on request retry.')
        obj._p_estimated_size = len(p)
