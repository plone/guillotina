import asyncio
import asyncpg
import logging
import ujson


class ReadOnlyError(Exception):
    pass


log = logging.getLogger("guillotina.storage")


GET_OID = """
    SELECT zoid, tid, state_size, resource, of, parent_id, id, type, state
    FROM objects
    WHERE zoid = $1::varchar(32)
    """

GET_SONS_KEYS = """
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

GET_ANNOTATION = """
    SELECT zoid, tid, state_size, resource, type, state, id
    FROM objects
    WHERE of = $1::varchar(32) AND id = $2::text
    """

MAX_TID = """
    SELECT max(tid) FROM objects
    """

MOVE_FROM_TEMP = """
    WITH moved_rows AS (
        DELETE FROM current_objects
        WHERE
            "tid" = $1::int
        RETURNING *
    )
    INSERT INTO objects
    SELECT * FROM moved_rows
    ON CONFLICT (zoid) DO UPDATE SET
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

INSERT_TEMP = """
    INSERT INTO current_objects
    (zoid, tid, state_size, part, resource, of, otid, parent_id, id, type, json, state)
    VALUES ($1::varchar(32), $2::int, $3::int, $4::int, $5::boolean, $6::varchar(32), $7::int,
    $8::varchar(32), $9::text, $10::text, $11::json, $12::bytea)
    """

NEXT_TID = "SELECT nextval('tid_seq');"

NUM_CHILDS = "SELECT count(*) FROM objects WHERE parent_id = $1::varchar(32)"

GET_CHILDS = """
    SELECT zoid, tid, state_size, resource, type, state, id
    FROM objects
    WHERE parent_id = $1::VARCHAR(32)
    """

DELETE_TMP = '''
    INSERT INTO delete_objects (zoid, tid) VALUES ($1::varchar(32), $2::int)
'''

DELETE_FROM_OBJECTS = """
    WITH deleted_rows AS (
        DELETE FROM delete_objects
        WHERE
            "tid" = $1::int
        RETURNING *
    )
    DELETE FROM objects WHERE zoid = (SELECT zoid FROM deleted_rows);
    """


class BaseStorage(object):

    _cache = {}
    _read_only = False

    def __init__(self, read_only=False):
        self._read_only = read_only

    def use_cache(self, value):
        self._cache = value

    def isReadOnly(self):
        return self._read_only


class APgStorage(BaseStorage):
    """Storage to a relational database, based on invalidation polling"""

    _dsn = None
    _partition_class = None
    _pool_size = None

    _pool = None

    _ltid = None
    _conn = None
    _lock = None

    _blobhelper = None
    _large_record_size = 1 << 24

    def __init__(self, dsn=None, partition=None, read_only=False, name=None,
                 pool_size=10):
        super(APgStorage, self).__init__(read_only)
        self._dsn = dsn
        self._pool_size = pool_size
        self._partition_class = partition
        self._read_only = read_only
        self.__name__ = name
        self._lock = asyncio.Lock()
        self._read_conn = None

    async def finalize(self):
        await self._pool.release(self._read_conn)
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
        stmt = """
            CREATE TABLE IF NOT EXISTS objects (
                zoid        VARCHAR(32) NOT NULL PRIMARY KEY,
                tid         BIGINT NOT NULL,
                state_size  BIGINT NOT NULL,
                part        BIGINT NOT NULL,
                resource    BOOLEAN NOT NULL,
                of          VARCHAR(32),
                otid        BIGINT,
                parent_id   VARCHAR(32) REFERENCES objects ON DELETE CASCADE,
                id          TEXT,
                type        TEXT NOT NULL,
                json        JSONB,
                state       BYTEA
            ) ;
            CREATE INDEX IF NOT EXISTS object_tid ON objects (tid);
            CREATE INDEX IF NOT EXISTS object_of ON objects (of);
            CREATE INDEX IF NOT EXISTS object_part ON objects (part);
            CREATE INDEX IF NOT EXISTS object_parent ON objects (parent_id);
            CREATE INDEX IF NOT EXISTS object_id ON objects (id);
            """

        func = """
        CREATE OR REPLACE FUNCTION create_partition_and_insert() RETURNS trigger AS
              $BODY$
                DECLARE
                  partition_id TEXT;
                  partition TEXT;
                BEGIN
                  partition_id := to_char(NEW.part);
                  partition := 'objects_' || partition_id;
                  IF NOT EXISTS(SELECT relname FROM pg_class WHERE relname=partition) THEN
                    RAISE NOTICE 'A partition has been created %',partition;
                    EXECUTE 'CREATE TABLE ' || partition ||
                        ' (check (part = ''' || NEW.part || ''')) INHERITS (objects);';
                  END IF;
                  EXECUTE 'INSERT INTO ' || partition ||
                    ' SELECT(objects ' || quote_literal(NEW) || ').* RETURNING patent_id;';
                  RETURN NULL;
                END;
              $BODY$
            LANGUAGE plpgsql VOLATILE
            COST 100;
            """

        zoid = """
            CREATE SEQUENCE IF NOT EXISTS zoid_seq;
            """
        tid = """
            CREATE SEQUENCE IF NOT EXISTS tid_seq;
            """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(stmt)
                await conn.execute(func)
                await conn.execute(zoid)
                await conn.execute(tid)

        self._read_conn = await self.open()
        self._stmt_next_tid = await self._read_conn.prepare(NEXT_TID)

    async def remove(self):
        """Reset the tables"""
        stmt = """DROP TABLE IF EXISTS objects;"""
        stmt1 = """ALTER SEQUENCE zoid_seq RESTART WITH 1;"""
        async with self._pool.acquire() as conn:
            await conn.execute(stmt)
            await conn.execute(stmt1)

    async def open(self):
        conn = await self._pool.acquire()
        return conn

    async def close(self, con):
        try:
            await self._pool.release(con)
        except asyncio.CancelledError:
            pass

    async def get_prepared_statement(self, txn, name, statement):
        '''
        lazy load prepared statements so we don't do unncessary
        calls to pg...
        '''
        name = '_smt_' + name
        if not hasattr(txn, name):
            setattr(txn, name, await txn._db_conn.prepare(statement))
        return getattr(txn, name)

    async def last_transaction(self, txn):
        smt = await self.get_prepared_statement(txn, 'max_tid', MAX_TID)
        value = await smt.fetchval()
        return 0 if value is None else value

    async def load(self, txn, oid):
        int_oid = oid
        smt = await self.get_prepared_statement(txn, 'get_oid', GET_OID)
        objects = await smt.fetchrow(int_oid)
        if objects is None:
            raise KeyError(oid)
        return objects

    async def tpc_begin(self, txn, conn):
        # Add the new tid
        if self._read_only:
            raise ReadOnlyError()

        txn._db_conn = conn
        txn._db_txn = conn.transaction()
        await txn._db_txn.start()

    async def precommit(self, txn):
        async with self._lock:
            tid = await self._stmt_next_tid.fetchval()
        if tid is not None:
            txn._tid = tid
        current = """
            CREATE TEMPORARY TABLE IF NOT EXISTS current_objects (
                zoid        VARCHAR(32) NOT NULL PRIMARY KEY,
                tid         BIGINT NOT NULL,
                state_size  BIGINT NOT NULL,
                part        BIGINT NOT NULL,
                resource    BOOLEAN NOT NULL,
                of          VARCHAR(32),
                otid        BIGINT,
                parent_id   VARCHAR(32),
                id          TEXT,
                type        TEXT NOT NULL,
                json        JSONB,
                state       BYTEA
            )  ON COMMIT DELETE ROWS;
            CREATE INDEX IF NOT EXISTS current_object_tid ON current_objects (tid);
            CREATE INDEX IF NOT EXISTS current_object_oid ON current_objects (zoid);
            CREATE TEMPORARY TABLE IF NOT EXISTS delete_objects (
                zoid        VARCHAR(32) NOT NULL PRIMARY KEY,
                tid         BIGINT NOT NULL
            ) ON COMMIT DELETE ROWS;
            """
        await txn._db_conn.execute(current)

    async def store(self, oid, old_serial, writer, obj, txn):
        assert oid is not None
        p = writer.serialize()  # This calls __getstate__ of obj
        if len(p) >= self._large_record_size:
            self._log.warn("Too long object %d" % (obj.__class__, len(p)))
        json_dict = await writer.get_json()
        json = ujson.dumps(json_dict)
        part = writer.part
        if part is None:
            part = 0
        # (zoid, tid, state_size, part, main, parent_id, type, json, state)
        output = await txn._db_conn.execute(  # noqa
            INSERT_TEMP,         # Insert on temp table
            oid,                 # The OID of the object
            txn._tid,            # Our TID
            len(p),              # Len of the object
            part,                # Partition indicator
            writer.resource,    # Is a resource ?
            writer.of,                # It belogs to a main
            old_serial,          # Old serial
            writer.parent_id,           # Parent OID
            writer.id,                  # Traversal ID
            writer.type,               # Guillotina type
            json,                # JSON catalog
            p                    # Pickle state
        )
        obj._p_estimated_size = len(p)
        return txn._tid, len(p)

    async def delete(self, txn, oid):
        await txn._db_conn.execute(
            DELETE_TMP,         # delete on temp table
            oid,
            txn._tid)

    async def tpc_vote(self, transaction):
        # Check if there is any commit bigger than the one we already have
        # For each object going to be written we need to check if it has
        # a new TID
        r = await transaction._db_conn.fetch(
            """
            SELECT ob.zoid, ob.tid FROM objects ob JOIN current_objects co
            USING (zoid) WHERE ob.tid > co.otid AND co.tid = $1""",
            transaction._tid)
        if len(r) == 0:
            return True
        else:
            return False

    async def tpc_finish(self, transaction):
        await transaction._db_conn.execute(
            MOVE_FROM_TEMP,
            transaction._tid
        )
        await transaction._db_conn.execute(
            DELETE_FROM_OBJECTS,
            transaction._tid
        )
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
        smt = await self.get_prepared_statement(txn, 'get_sons_keys', GET_SONS_KEYS)
        result = await smt.fetch(oid)
        return result

    async def get_child(self, txn, parent_id, id):
        smt = await self.get_prepared_statement(txn, 'get_child', GET_CHILD)
        result = await smt.fetchrow(parent_id, id)
        return result

    async def has_key(self, txn, parent_id, id):
        smt = await self.get_prepared_statement(txn, 'exist_child', EXIST_CHILD)
        result = await smt.fetchrow(parent_id, id)
        if result is None:
            return False
        else:
            return True

    async def len(self, txn, oid):
        smt = await self.get_prepared_statement(txn, 'num_childs', NUM_CHILDS)
        result = await smt.fetchval(oid)
        return result

    async def items(self, txn, oid):
        smt = await self.get_prepared_statement(txn, 'get_childs', GET_CHILDS)
        async for record in smt.cursor(oid):
            yield record

    async def get_annotation(self, txn, oid, id):
        smt = await self.get_prepared_statement(txn, 'get_annotation', GET_ANNOTATION)
        result = await smt.fetchrow(oid, id)
        return result

    async def get_annotation_keys(self, txn, oid):
        smt = await self.get_prepared_statement(
            txn, 'get_annotations_keys', GET_ANNOTATIONS_KEYS)
        result = await smt.fetch(oid)
        return result
