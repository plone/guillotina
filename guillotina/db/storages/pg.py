from asyncio import shield
from guillotina import glogging
from guillotina import metrics
from guillotina._settings import app_settings
from guillotina.const import TRASHED_ID
from guillotina.db.events import StorageCreatedEvent
from guillotina.db.interfaces import IPostgresStorage
from guillotina.db.storages.base import BaseStorage
from guillotina.db.storages.utils import clear_table_name
from guillotina.db.storages.utils import get_table_definition
from guillotina.db.storages.utils import register_sql
from guillotina.db.storages.utils import SQLStatements
from guillotina.db.uid import MAX_UID_LENGTH
from guillotina.event import notify
from guillotina.exceptions import ConflictError
from guillotina.exceptions import ConflictIdOnContainer
from guillotina.exceptions import TIDConflictError
from guillotina.profile import profilable
from zope.interface import implementer

import asyncio
import asyncpg
import asyncpg.connection
import concurrent
import time
import ujson


try:
    import prometheus_client
    from prometheus_client.utils import INF

    PG_OPS = prometheus_client.Counter(
        "guillotina_db_pg_ops_total",
        "Total count of ops by type of operation and the error if there was.",
        labelnames=["type", "error"],
    )
    PG_OPS_PROCESSING_TIME = prometheus_client.Histogram(
        "guillotina_db_pg_ops_processing_time_seconds",
        "Histogram of operations processing time by type (in seconds)",
        labelnames=["type"],
        buckets=(
            0.005,
            0.01,
            0.025,
            0.05,
            0.075,
            0.1,
            0.25,
            0.5,
            0.75,
            1.0,
            2.5,
            5.0,
            7.5,
            10.0,
            30.0,
            60.0,
            INF,
        ),
    )
    PG_LOCK_ACQUIRE_TIME = prometheus_client.Histogram(
        "guillotina_db_pg_lock_time_seconds",
        "Histogram of time it takes to acquire locks (in seconds)",
        labelnames=["type"],
        buckets=(0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, INF),
    )

    class watch(metrics.watch):
        def __init__(self, operation: str):
            super().__init__(
                counter=PG_OPS,
                histogram=PG_OPS_PROCESSING_TIME,
                labels={"type": operation},
                error_mappings={
                    "undefined_table_error": asyncpg.exceptions.UndefinedTableError,
                    "connection_error": asyncpg.exceptions.PostgresConnectionError,
                    "interface_error": asyncpg.exceptions.InterfaceError,
                    "unique_key_error": asyncpg.exceptions.UniqueViolationError,
                    "foreign_key_error": asyncpg.exceptions.ForeignKeyViolationError,
                    "deadlock_error": asyncpg.exceptions.DeadlockDetectedError,
                },
            )

    class watch_lock(metrics.watch_lock):
        def __init__(self, lock: asyncio.Lock, operation: str):
            super().__init__(lock, PG_LOCK_ACQUIRE_TIME, labels={"type": operation})


except ImportError:
    watch = metrics.dummy_watch  # type: ignore

    class watch_lock(metrics.watch_lock):  # type: ignore
        def __init__(self, lock: asyncio.Lock, operation: str):
            super().__init__(lock, histogram=None)


log = glogging.getLogger("guillotina.storage")


# we can not use FOR UPDATE or FOR SHARE unfortunately because
# it can cause deadlocks on the database--we need to resolve them ourselves
register_sql(
    "GET_OID",
    f"""
SELECT zoid, tid, state_size, resource, of, parent_id, id, type, state
FROM {{table_name}}
WHERE zoid = $1::varchar({MAX_UID_LENGTH})
""",
)

register_sql(
    "GET_CHILDREN_KEYS",
    f"""
SELECT id
FROM {{table_name}}
WHERE parent_id = $1::varchar({MAX_UID_LENGTH})
""",
)


register_sql(
    "GET_ANNOTATIONS_KEYS",
    f"""
SELECT id, parent_id
FROM {{table_name}}
WHERE of = $1::varchar({MAX_UID_LENGTH})
""",
)

register_sql(
    "GET_CHILD",
    f"""
SELECT zoid, tid, state_size, resource, type, state, id, parent_id, of
FROM {{table_name}}
WHERE parent_id = $1::varchar({MAX_UID_LENGTH}) AND id = $2::text
""",
)

register_sql(
    "GET_CHILDREN_BATCH",
    f"""
SELECT zoid, tid, state_size, resource, type, state, id, parent_id, of
FROM {{table_name}}
WHERE parent_id = $1::varchar({MAX_UID_LENGTH}) AND id = ANY($2)
""",
)

register_sql(
    "EXIST_CHILD",
    f"""
SELECT zoid
FROM {{table_name}}
WHERE parent_id = $1::varchar({MAX_UID_LENGTH}) AND id = $2::text
""",
)


register_sql(
    "HAS_OBJECT",
    f"""
SELECT zoid
FROM {{table_name}}
WHERE zoid = $1::varchar({MAX_UID_LENGTH})
""",
)


register_sql(
    "GET_ANNOTATION",
    f"""
SELECT zoid, tid, state_size, resource, type, state, id, parent_id, of
FROM {{table_name}}
WHERE
    of = $1::varchar({MAX_UID_LENGTH}) AND
    id = $2::text
""",
)


def _wrap_return_count(txt):
    return """WITH rows AS (
{}
    RETURNING 1
)
SELECT count(*) FROM rows""".format(
        txt
    )


# upsert without checking matching tids on updated object
NAIVE_UPSERT = f"""
INSERT INTO {{table_name}}
(zoid, tid, state_size, part, resource, of, otid, parent_id, id, type, json, state)
VALUES ($1::varchar({MAX_UID_LENGTH}), $2::bigint, $3::int, $4::int, $5::boolean,
        $6::varchar({MAX_UID_LENGTH}), $7::bigint, $8::varchar({MAX_UID_LENGTH}),
        $9::text, $10::text, $11::json, $12::bytea)
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
register_sql(
    "UPSERT",
    _wrap_return_count(
        NAIVE_UPSERT
        + """
WHERE
    tid = EXCLUDED.otid"""
    ),
)
register_sql("NAIVE_UPSERT", _wrap_return_count(NAIVE_UPSERT))


# update without checking matching tids on updated object
NAIVE_UPDATE = f"""
UPDATE {{table_name}}
SET
    tid = $2::bigint,
    state_size = $3::int,
    part = $4::int,
    resource = $5::boolean,
    of = $6::varchar({MAX_UID_LENGTH}),
    otid = $7::bigint,
    parent_id = $8::varchar({MAX_UID_LENGTH}),
    id = $9::text,
    type = $10::text,
    json = $11::json,
    state = $12::bytea
WHERE
    zoid = $1::varchar({MAX_UID_LENGTH})"""
register_sql("UPDATE", _wrap_return_count(NAIVE_UPDATE + """ AND tid = $7::bigint"""))
register_sql("NAIVE_UPDATE", _wrap_return_count(NAIVE_UPDATE))


register_sql(
    "NUM_CHILDREN", f"SELECT count(*) FROM {{table_name}} WHERE parent_id = $1::varchar({MAX_UID_LENGTH})"
)


register_sql("NUM_ROWS", "SELECT count(*) FROM {table_name}")


register_sql("NUM_RESOURCES", "SELECT count(*) FROM {table_name} WHERE resource is TRUE")

register_sql("NUM_RESOURCES_BY_TYPE", "SELECT count(*) FROM {table_name} WHERE type=$1::TEXT")

register_sql(
    "RESOURCES_BY_TYPE",
    """
SELECT zoid, tid, state_size, resource, type, state, id
FROM {table_name}
WHERE type=$1::TEXT
ORDER BY zoid
LIMIT $2::int
OFFSET $3::int
""",
)


register_sql(
    "GET_CHILDREN",
    f"""
SELECT zoid, tid, state_size, resource, type, state, id
FROM {{table_name}}
WHERE parent_id = $1::VARCHAR({MAX_UID_LENGTH})
""",
)


register_sql(
    "TRASH_PARENT_ID",
    f"""
UPDATE {{table_name}}
SET
    parent_id = '{TRASHED_ID}'
WHERE
    zoid = $1::varchar({MAX_UID_LENGTH})
""",
)


register_sql(
    "INSERT_BLOB_CHUNK",
    f"""
INSERT INTO {{table_name}}
(bid, zoid, chunk_index, data)
VALUES ($1::VARCHAR({MAX_UID_LENGTH}), $2::VARCHAR({MAX_UID_LENGTH}),
        $3::INT, $4::BYTEA)
""",
)


register_sql(
    "READ_BLOB_CHUNK",
    f"""
SELECT * from {{table_name}}
WHERE bid = $1::VARCHAR({MAX_UID_LENGTH})
AND chunk_index = $2::int
""",
)


register_sql(
    "DELETE_BLOB",
    f"""
DELETE FROM {{table_name}} WHERE bid = $1::VARCHAR({MAX_UID_LENGTH});
""",
)


TXN_CONFLICTS = """
    SELECT zoid, tid, state_size, resource, type, id
    FROM {table_name}
    WHERE tid > $1"""
register_sql("TXN_CONFLICTS", TXN_CONFLICTS)

register_sql("TXN_CONFLICTS_ON_OIDS", TXN_CONFLICTS + " AND zoid = ANY($2)")


register_sql(
    "BATCHED_GET_CHILDREN_KEYS",
    f"""
SELECT id
FROM {{table_name}}
WHERE parent_id = $1::varchar({MAX_UID_LENGTH})
ORDER BY zoid
LIMIT $2::int
OFFSET $3::int
""",
)

register_sql(
    "DELETE_OBJECT",
    f"""
DELETE FROM {{table_name}}
WHERE zoid = $1::varchar({MAX_UID_LENGTH});
""",
)

register_sql(
    "GET_TRASHED_OBJECTS",
    f"""
SELECT zoid from {{table_name}} where parent_id = '{TRASHED_ID}';
""",
)

register_sql(
    "CREATE_TRASH",
    f"""
INSERT INTO {{table_name}} (zoid, tid, state_size, part, resource, type)
SELECT '{TRASHED_ID}', 0, 0, 0, FALSE, 'TRASH_REF'
WHERE NOT EXISTS (SELECT * FROM {{table_name}} WHERE zoid = '{TRASHED_ID}')
RETURNING id;
""",
)


def restart_conn_on_exception(f):
    async def decorator(self: "PostgresqlStorage", *args, **kwargs):
        try:
            return await f(self, *args, **kwargs)
        except (asyncpg.exceptions.PostgresConnectionError, asyncpg.exceptions.InterfaceError) as ex:
            await self._check_bad_connection(ex)
            raise

    return decorator


# how long to wait before trying to recover bad connections
BAD_CONNECTION_RESTART_DELAY = 0.25


class LightweightConnection(asyncpg.connection.Connection):
    """
    See asyncpg.connection.Connection._get_reset_query to see
    details of the point of this.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # we purposefully do not support these options for performance
        self._server_caps = asyncpg.connection.ServerCapabilities(
            advisory_locks=False,
            notifications=False,
            sql_reset=False,
            sql_close_all=self._server_caps.sql_close_all,
            plpgsql=self._server_caps.plpgsql,
        )

    async def add_listener(self, channel, callback):
        raise NotImplementedError("Does not support listeners")

    async def remove_listener(self, channel, callback):
        raise NotImplementedError("Does not support listeners")


class PGVacuum:
    def __init__(self, manager, loop):
        self._manager = manager
        self._loop = loop
        self._queue = asyncio.Queue(loop=loop)
        self._closed = False
        self._active = False
        self._sql = SQLStatements()

    async def initialize(self):
        while not self._closed:
            try:
                await self._initialize()
            except (concurrent.futures.CancelledError, RuntimeError):
                # we're okay with the task getting cancelled
                return

    async def _initialize(self):
        while not self._closed:
            oid = None
            try:
                oid, table_name = await self._queue.get()
                self._active = True
                await shield(self.vacuum(oid, table_name))
            except (concurrent.futures.CancelledError, RuntimeError):
                raise
            except Exception:
                log.warning(f"Error vacuuming oid {oid}", exc_info=True)
            finally:
                self._active = False
                try:
                    self._queue.task_done()
                except ValueError:
                    pass

    async def run(self, table_name):
        """
        get existing trashed objects, push them on the queue...
        there might be contention, but that is okay
        """
        async with self._manager.pool.acquire(timeout=self._manager._conn_acquire_timeout) as conn:
            try:
                sql = self._sql.get("GET_TRASHED_OBJECTS", table_name)
                for record in await conn.fetch(sql):
                    self._queue.put_nowait((record["zoid"], table_name))
            except concurrent.futures.TimeoutError:
                log.info("Timed out connecting to storage")
            except Exception:
                log.warning("Error deleting trashed object", exc_info=True)

    async def add_to_queue(self, oid, table_name):
        if self._closed:
            raise Exception("Closing down")
        await self._queue.put((oid, table_name))

    async def vacuum(self, oid, table_name):
        """
        DELETED objects has parent id changed to the trashed ob for the oid...
        """
        async with self._manager.pool.acquire(timeout=self._manager._conn_acquire_timeout) as conn:
            sql = self._sql.get("DELETE_OBJECT", table_name)
            try:
                with watch("vacuum_object"):
                    await conn.execute(sql, oid)
            except Exception:
                log.warning("Error deleting trashed object", exc_info=True)

    async def finalize(self):
        self._closed = True
        try:
            await asyncio.wait_for(self._queue.join(), 2)
        except asyncio.TimeoutError:
            pass

    @property
    def size(self):
        return self._queue.qsize()


class PGConnectionManager:
    """
    class to manage pool of connections
    """

    _next_tid_sql = "SELECT nextval('{schema}.tid_sequence');"
    _max_tid_sql = "SELECT last_value FROM {schema}.tid_sequence;"

    def __init__(
        self,
        dsn=None,
        pool_size=13,
        connection_options=None,
        conn_acquire_timeout=20,
        vacuum_class=PGVacuum,
        autovacuum=True,
        db_schema="public",
    ):
        self._dsn = dsn
        self._pool_size = pool_size
        self._pool = None
        self._read_conn = None
        self._connection_options = connection_options or {}
        self._conn_acquire_timeout = conn_acquire_timeout
        self._lock = asyncio.Lock()
        self._closable = True
        self._vacuum = None
        self._vacuum_task = None
        self._vacuum_class = vacuum_class
        self._autovacuum = autovacuum
        self._stmt_next_tid = self._stmt_max_tid = None
        self._db_schema = db_schema

    @property
    def vacuum(self):
        return self._vacuum

    @property
    def read_conn(self):
        return self._read_conn

    @property
    def pool(self):
        return self._pool

    @property
    def stmt_next_tid(self):
        return self._stmt_next_tid

    @property
    def stmt_max_tid(self):
        return self._stmt_max_tid

    @property
    def lock(self):
        return self._lock

    async def close(self):
        async with watch_lock(self._lock, "shared_close_conn"):
            if self._pool is None:
                # nothing to close
                return
            if not self._closable:
                # prevent closing
                return

            if self._vacuum is not None:
                await self._vacuum.finalize()
                self._vacuum_task.cancel()
                self._vacuum = self._vacuum_task = None

            try:
                with watch("release_connection"):
                    await shield(self._pool.release(self._read_conn))
            except asyncpg.exceptions.InterfaceError:
                pass
            # terminate force closes all these
            # this step is happening at the end of application shutdown and
            # connections should not be staying open at this step
            self._pool.terminate()
            self._pool = self._read_conn = None

    async def _initialize_tid_statements(self, retried=False):
        try:
            self._stmt_next_tid = await self._read_conn.prepare(
                self._next_tid_sql.format(schema=self._db_schema)
            )
            self._stmt_max_tid = await self._read_conn.prepare(
                self._max_tid_sql.format(schema=self._db_schema)
            )
        except (asyncpg.exceptions.UndefinedTableError, asyncpg.exceptions.InvalidSchemaNameError):
            if retried:  # pragma: no cover
                # always good to have prevention of infinity recursion
                raise Exception("Error creating tid_sequence, this should never happen", exc_info=True)
            async with self.pool.acquire(timeout=self._conn_acquire_timeout) as conn:
                if self._db_schema != "public":
                    await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self._db_schema}")
                await conn.execute(
                    "CREATE SEQUENCE IF NOT EXISTS {schema}.tid_sequence;".format(schema=self._db_schema)
                )
            await self._initialize_tid_statements(True)

    async def initialize(self, loop=None, **kw):
        async with watch_lock(self._lock, "shared_initialize"):
            if self._pool is not None:
                # nothing to open
                return
            self._connection_options = kw
            if loop is None:
                loop = asyncio.get_event_loop()
            self._pool = await asyncpg.create_pool(
                dsn=self._dsn,
                max_size=self._pool_size,
                min_size=2,
                connection_class=app_settings["pg_connection_class"],
                loop=loop,
                **kw,
            )

            # shared read connection on all transactions
            self._read_conn = await self._pool.acquire(timeout=self._conn_acquire_timeout)
            await self._initialize_tid_statements()

            if self._autovacuum:
                self._vacuum = self._vacuum_class(self, loop)
                self._vacuum_task = asyncio.Task(self._vacuum.initialize(), loop=loop)

    async def restart(self, timeout=2):
        # needs to be used with lock
        if self._pool is not None:
            try:
                await asyncio.wait_for(self._pool.close(), timeout)
            except asyncio.TimeoutError:
                pass
            self._pool.terminate()

        # re-bind, throw conflict error so the request is restarted...
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            max_size=self._pool_size,
            min_size=2,
            connection_class=app_settings["pg_connection_class"],
            **self._connection_options,
        )

        # shared read connection on all transactions
        self._read_conn = await self._pool.acquire(timeout=self._conn_acquire_timeout)
        await self._initialize_tid_statements()


@implementer(IPostgresStorage)
class PostgresqlStorage(BaseStorage):
    """Storage to a relational database, based on invalidation polling"""

    _dsn = None
    _partition_class = None
    _large_record_size = 1 << 24
    _vacuum_class = PGVacuum
    _connection_manager_class = PGConnectionManager
    _objects_table_name = "objects"
    _blobs_table_name = "blobs"

    _object_schema = {
        "zoid": f"VARCHAR({MAX_UID_LENGTH}) NOT NULL PRIMARY KEY",
        "tid": "BIGINT NOT NULL",
        "state_size": "BIGINT NOT NULL",
        "part": "BIGINT NOT NULL",
        "resource": "BOOLEAN NOT NULL",
        "of": f"VARCHAR({MAX_UID_LENGTH}) REFERENCES {{objects_table_name}} ON DELETE CASCADE",
        "otid": "BIGINT",
        "parent_id": f"VARCHAR({MAX_UID_LENGTH}) REFERENCES {{objects_table_name}} ON DELETE CASCADE",  # noqa
        "id": "TEXT",
        "type": "TEXT NOT NULL",
        "json": "JSONB",
        "state": "BYTEA",
    }

    _blob_schema = {
        "bid": f"VARCHAR({MAX_UID_LENGTH}) NOT NULL",
        "zoid": f"VARCHAR({MAX_UID_LENGTH}) NOT NULL REFERENCES {{objects_table_name}} ON DELETE CASCADE",
        "chunk_index": "INT NOT NULL",
        "data": "BYTEA",
    }

    _initialize_statements = [
        "CREATE INDEX IF NOT EXISTS {object_table_name}_tid ON {objects_table_name} (tid);",
        "CREATE INDEX IF NOT EXISTS {object_table_name}_of ON {objects_table_name} (of);",
        "CREATE INDEX IF NOT EXISTS {object_table_name}_part ON {objects_table_name} (part);",
        "CREATE INDEX IF NOT EXISTS {object_table_name}_parent ON {objects_table_name} (parent_id);",
        "CREATE INDEX IF NOT EXISTS {object_table_name}_id ON {objects_table_name} (id);",
        "CREATE INDEX IF NOT EXISTS {object_table_name}_type ON {objects_table_name} (type);",
        "CREATE INDEX IF NOT EXISTS {blob_table_name}_bid ON {blobs_table_name} (bid);",
        "CREATE INDEX IF NOT EXISTS {blob_table_name}_zoid ON {blobs_table_name} (zoid);",
        "CREATE INDEX IF NOT EXISTS {blob_table_name}_chunk ON {blobs_table_name} (chunk_index);",
        "ALTER TABLE {objects_table_name} ADD CONSTRAINT {object_table_name}_parent_id_zoid_check CHECK (parent_id != zoid) NOT VALID;",  # noqa
    ]

    _unique_constraints = [
        """CREATE UNIQUE INDEX CONCURRENTLY {constraint_name}_parent_id_id_key
           ON {objects_table_name} (parent_id, id)
           WHERE parent_id != '{TRASHED_ID}' """,
        """CREATE UNIQUE INDEX CONCURRENTLY {constraint_name}_annotations_unique ON {objects_table_name} (of, id);""",
    ]

    def __init__(
        self,
        dsn=None,
        partition=None,
        read_only=False,
        name=None,
        pool_size=13,
        transaction_strategy="resolve_readcommitted",
        conn_acquire_timeout=20,
        conn_release_timeout=60,
        db_schema="public",
        store_json=True,
        objects_table_name="objects",
        blobs_table_name="blobs",
        connection_manager=None,
        autovacuum=True,
        **options,
    ):
        super(PostgresqlStorage, self).__init__(read_only, transaction_strategy=transaction_strategy)
        self._dsn = dsn
        self._pool_size = pool_size
        self._partition_class = partition
        self._read_only = read_only
        self.__name__ = name
        self._conn_acquire_timeout = conn_acquire_timeout
        self._conn_release_timeout = conn_release_timeout
        self._options = options
        self._store_json = store_json
        self._connection_options = {}
        self._connection_initialized_on = time.time()
        self._db_schema = db_schema
        self._objects_table_name = f"{db_schema}.{objects_table_name}"
        self._blobs_table_name = f"{db_schema}.{blobs_table_name}"
        self._sql = SQLStatements()
        self._connection_manager = connection_manager
        self._autovacuum = autovacuum

    async def finalize(self):
        await self._connection_manager.close()

    @property
    def sql(self):
        return self._sql

    @property
    def read_conn(self):
        return self._connection_manager.read_conn

    @property
    def pool(self):
        return self._connection_manager.pool

    @property
    def connection_manager(self):
        return self._connection_manager

    @property
    def lock(self):
        return self._connection_manager.lock

    @property
    def stmt_next_tid(self):
        return self._connection_manager._stmt_next_tid

    @property
    def stmt_max_tid(self):
        return self._connection_manager._stmt_max_tid

    @property
    def objects_table_name(self):
        return self._objects_table_name

    async def create(self, conn=None):
        if conn is None:
            conn = self.read_conn
        # Check DB
        log.info("Creating initial database objects")

        statements = []

        if self._db_schema and self._db_schema != "public":
            statements.extend([f"CREATE SCHEMA IF NOT EXISTS {self._db_schema}"])

        statements.extend(
            [
                get_table_definition(self._objects_table_name, self._object_schema),
                get_table_definition(
                    self._blobs_table_name, self._blob_schema, primary_keys=("bid", "zoid", "chunk_index")
                ),
            ]
        )
        statements.extend(self._initialize_statements)

        with watch("create_db"):
            for statement in statements:
                otable_name = clear_table_name(self._objects_table_name)
                if otable_name == "objects":
                    otable_name = "object"
                btable_name = clear_table_name(self._blobs_table_name)
                if btable_name == "blobs":
                    btable_name = "blob"
                statement = statement.format(
                    objects_table_name=self._objects_table_name,
                    blobs_table_name=self._blobs_table_name,
                    # singular, index names
                    object_table_name=otable_name,
                    blob_table_name=btable_name,
                    schema=self._db_schema,
                )
                try:
                    await conn.execute(statement)
                except asyncpg.exceptions.UniqueViolationError:
                    # this is okay on creation, means 2 getting created at same time
                    pass

    async def restart_connection(self, timeout=0.1):
        log.error("Connection potentially lost to pg, restarting")
        await self._connection_manager.restart()
        self._connection_initialized_on = time.time()
        raise ConflictError("Restarting connection to postgresql")

    async def has_unique_constraint(self, conn):
        table_name = clear_table_name(self._objects_table_name)
        result = await conn.fetch(
            """
SELECT * FROM pg_indexes
WHERE tablename = '{}' AND indexname = '{}_parent_id_id_key';
""".format(
                table_name, table_name
            )
        )
        return len(result) > 0

    async def initialize(self, loop=None, **kw):
        self._connection_options = kw
        if self._connection_manager is None:
            self._connection_manager = self._connection_manager_class(
                dsn=self._dsn,
                pool_size=self._pool_size,
                connection_options=self._connection_options,
                conn_acquire_timeout=self._conn_acquire_timeout,
                vacuum_class=self._vacuum_class,
                autovacuum=self._autovacuum,
                db_schema=self._db_schema,
            )
            await self._connection_manager.initialize(loop, **kw)

        with watch("initialize_db"):
            async with self.pool.acquire(timeout=self._conn_acquire_timeout) as conn:
                if await self.has_unique_constraint(conn):
                    self._supports_unique_constraints = True

                trash_sql = self._sql.get("CREATE_TRASH", self._objects_table_name)
                try:
                    await conn.execute(trash_sql)
                except asyncpg.exceptions.ReadOnlySQLTransactionError:
                    # Not necessary for read-only pg
                    pass
                except (asyncpg.exceptions.UndefinedTableError, asyncpg.exceptions.InvalidSchemaNameError):
                    async with conn.transaction():
                        await self.create(conn)
                        # only available on new databases
                        for constraint in self._unique_constraints:
                            await conn.execute(
                                constraint.format(
                                    objects_table_name=self._objects_table_name,
                                    constraint_name=clear_table_name(self._objects_table_name),
                                    TRASHED_ID=TRASHED_ID,
                                ).replace("CONCURRENTLY", "")
                            )
                        self._supports_unique_constraints = True
                        await conn.execute(trash_sql)
                        await notify(StorageCreatedEvent(self, db_conn=conn))

        self._connection_initialized_on = time.time()

    async def remove(self):
        """Reset the tables"""
        async with self.pool.acquire(timeout=self._conn_acquire_timeout) as conn:
            await conn.execute("DROP TABLE IF EXISTS {} CASCADE;".format(self._blobs_table_name))
            await conn.execute("DROP TABLE IF EXISTS {} CASCADE;".format(self._objects_table_name))

    @restart_conn_on_exception
    async def open(self):
        with watch("acquire_connection"):
            return await self.pool.acquire(timeout=self._conn_acquire_timeout)

    async def _close(self, con):
        try:
            with watch("release_connection"):
                await self.pool.release(con, timeout=self._conn_release_timeout)
        except asyncpg.exceptions.InterfaceError as ex:  # pragma: no cover
            if "received invalid connection" in str(ex):
                # ignore, new pool was created so we can not close this conn
                pass
            else:
                raise
        except Exception:  # pragma: no cover
            # unhandled, still try to terminate
            log.warning("Exception when closing connection", exc_info=True)
            try:
                con.terminate()
            except asyncpg.exceptions.InterfaceError as ex:
                if "released back to the pool" in str(ex):
                    pass
                else:
                    raise

    async def close(self, con):
        # we should never worry about correctly closing a connection
        asyncio.ensure_future(self._close(con))

    async def terminate(self, conn):
        log.warning(f"Terminate connection {conn}", exc_info=True)
        conn.terminate()

    async def load(self, txn, oid):
        sql = self._sql.get("GET_OID", self._objects_table_name)
        async with watch_lock(txn._lock, "load_object_by_oid"):
            objects = await self.get_one_row(txn, sql, oid, metric="load_object_by_oid")
        if objects is None:
            raise KeyError(oid)
        return objects

    @profilable
    async def store(self, oid, old_serial, writer, obj, txn):
        assert oid is not None

        pickled = writer.serialize()  # This calls __getstate__ of obj
        if len(pickled) >= self._large_record_size:
            log.info(f"Large object {obj.__class__}: {len(pickled)}")
        if self._store_json:
            json_dict = await writer.get_json()
            json = ujson.dumps(json_dict)
        else:
            json = None
        part = writer.part
        if part is None:
            part = 0

        update = False
        statement_sql = self._sql.get("NAIVE_UPSERT", self._objects_table_name)
        if not obj.__new_marker__ and obj.__serial__ is not None:
            # we should be confident this is an object update
            statement_sql = self._sql.get("UPDATE", self._objects_table_name)
            update = True

        conn = await txn.get_connection()
        async with watch_lock(txn._lock, "store_object"):
            try:
                with watch("store_object"):
                    result = await conn.fetch(
                        statement_sql,
                        oid,  # The OID of the object
                        txn._tid,  # Our TID
                        len(pickled),  # Len of the object
                        part,  # Partition indicator
                        writer.resource,  # Is a resource ?
                        writer.of,  # It belogs to a main
                        old_serial,  # Old serial
                        writer.parent_id,  # Parent OID
                        writer.id,  # Traversal ID
                        writer.type,  # Guillotina type
                        json,  # JSON catalog
                        pickled,  # Pickle state)
                    )
            except asyncpg.exceptions.UniqueViolationError as ex:
                if "Key (parent_id, id)" in ex.detail or "Key (of, id)" in ex.detail:
                    raise ConflictIdOnContainer(ex)
                raise
            except asyncpg.exceptions.ForeignKeyViolationError:
                txn.deleted[obj.__uuid__] = obj
                raise TIDConflictError(
                    "Bad value inserting into database that could be caused "
                    "by a bad cache value. This should resolve on request retry.",
                    oid,
                    txn,
                    old_serial,
                    writer,
                )
            except asyncpg.exceptions._base.InterfaceError as ex:
                if "another operation is in progress" in ex.args[0]:
                    raise ConflictError(
                        "asyncpg error, another operation in progress.", oid, txn, old_serial, writer
                    )
                raise
            except asyncpg.exceptions.DeadlockDetectedError:
                raise ConflictError("Deadlock detected.", oid, txn, old_serial, writer)
            if len(result) != 1 or result[0]["count"] != 1:
                if update:
                    # raise tid conflict error
                    raise TIDConflictError(
                        "Mismatch of tid of object being updated. This is likely "
                        "caused by a cache invalidation race condition and should "
                        "be an edge case. This should resolve on request retry.",
                        oid,
                        txn,
                        old_serial,
                        writer,
                    )
                else:
                    log.error(
                        "Incorrect response count from database update. "
                        "This should not happen. tid: {}".format(txn._tid)
                    )
        await txn._cache.store_object(obj, pickled)

    async def _txn_oid_commit_hook(self, status, oid):
        if self._connection_manager._vacuum is not None:
            await self._connection_manager._vacuum.add_to_queue(oid, self._objects_table_name)

    async def delete(self, txn, oid):
        conn = await txn.get_connection()
        sql = self._sql.get("TRASH_PARENT_ID", self._objects_table_name)
        async with watch_lock(txn._lock, "delete_object"):
            # for delete, we reassign the parent id and delete in the vacuum task
            with watch("delete_object"):
                await conn.execute(sql, oid)
        if self._autovacuum:
            txn.add_after_commit_hook(self._txn_oid_commit_hook, oid)

    async def _check_bad_connection(self, ex):
        # we do not use transaction lock here but a storage lock because
        # a storage object has a shard conn for reads
        for err in ("connection is closed", "pool is closed", "connection was closed"):
            if err in str(ex):
                if (time.time() - self._connection_initialized_on) > BAD_CONNECTION_RESTART_DELAY:
                    # we need to make sure we aren't calling this over and over again
                    async with watch_lock(self.lock, "shared_restart_conn"):
                        return await self.restart_connection()

    @restart_conn_on_exception
    async def get_next_tid(self, txn):
        async with watch_lock(self.lock, "shared_next_tid"):
            with watch("next_tid"):
                return await self.stmt_next_tid.fetchval()

    @restart_conn_on_exception
    async def get_current_tid(self, txn):
        async with watch_lock(self.lock, "shared_current_tid"):
            with watch("current_tid"):
                return await self.stmt_max_tid.fetchval()

    async def get_one_row(self, txn, sql, *args, prepare=False, metric="get_one_row"):
        conn = await txn.get_connection()
        # Helper function to provide easy adaptation to cockroach
        if prepare:
            # latest version of asyncpg has prepare bypassing statement cache
            with watch(metric + "_prepare"):
                smt = await conn.prepare(sql)
            with watch(metric):
                return await smt.fetchrow(*args)
        else:
            with watch(metric):
                return await conn.fetchrow(sql, *args)

    def _db_transaction_factory(self, txn):
        # make sure asycpg knows this is a new transaction
        if txn._db_conn._con is not None:
            txn._db_conn._con._top_xact = None
        return txn._db_conn.transaction(readonly=txn._manager._storage._read_only)

    @restart_conn_on_exception
    async def _async_db_transaction_factory(self, txn):
        return self._db_transaction_factory(txn)

    async def start_transaction(self, txn, retries=0):
        error = None
        conn = await txn.get_connection()
        async with watch_lock(txn._lock, "start_txn"):
            txn._db_txn = await self._async_db_transaction_factory(txn)

            try:
                with watch("start_txn"):
                    await txn._db_txn.start()
                return
            except (asyncpg.exceptions.InterfaceError, asyncpg.exceptions.InternalServerError) as ex:
                error = ex

        if error is not None:
            if retries > 2:
                raise error  # pylint: disable=E0702

            restart = rollback = False
            if isinstance(error, asyncpg.exceptions.InternalServerError):
                restart = True
                if error.sqlstate == "XX000":
                    rollback = True
            elif "manually started transaction" in error.args[0] or "connection is closed" in error.args[0]:
                restart = True
                if "manually started transaction" in error.args[0]:
                    rollback = True

            if rollback:
                try:
                    # thinks we're manually in txn, manually rollback and try again...
                    await conn.execute("ROLLBACK;")
                except asyncpg.exceptions._base.InterfaceError:
                    # we're okay with this error here...
                    pass
            if restart:
                await self.close(conn)
                txn._db_conn = await self.open()
                return await self.start_transaction(txn, retries + 1)

    async def get_conflicts(self, txn):
        async with watch_lock(self.lock, "shared_conflicts"):
            if len(txn.modified) == 0:
                return []
            # use storage lock instead of transaction lock
            if len(txn.modified) < 1000:
                # if it's too large, we're not going to check on object ids
                modified_oids = [k for k in txn.modified.keys()]
                sql = self._sql.get("TXN_CONFLICTS_ON_OIDS", self._objects_table_name)
                with watch("get_conflicts_oids"):
                    return await self.read_conn.fetch(sql, txn._tid, modified_oids)
            else:
                sql = self._sql.get("TXN_CONFLICTS", self._objects_table_name)
                with watch("get_conflicts"):
                    return await self.read_conn.fetch(sql, txn._tid)

    async def commit(self, transaction):
        async with watch_lock(transaction._lock, "commit_txn"):
            if transaction._db_txn is not None:
                with watch("commit_txn"):
                    await transaction._db_txn.commit()
            elif self._transaction_strategy not in ("none", "tidonly") and not transaction._skip_commit:
                log.warning("Do not have db transaction to commit")
            return transaction._tid

    async def abort(self, transaction):
        async with watch_lock(transaction._lock, "rollback_txn"):
            if transaction._db_txn is not None:
                try:
                    with watch("rollback_txn"):
                        await transaction._db_txn.rollback()
                except asyncpg.exceptions._base.InterfaceError:
                    # we're okay with this error here...
                    pass
        # reads don't need transaction necessarily so don't log
        # else:
        #     log.warning('Do not have db transaction to rollback')

    # Introspection
    async def get_page_of_keys(self, txn, oid, page=1, page_size=1000):
        conn = await txn.get_connection()
        keys = []
        sql = self._sql.get("BATCHED_GET_CHILDREN_KEYS", self._objects_table_name)
        with watch("page_of_keys"):
            for record in await conn.fetch(sql, oid, page_size, (page - 1) * page_size):
                keys.append(record["id"])
        return keys

    async def keys(self, txn, oid):
        conn = await txn.get_connection()
        sql = self._sql.get("GET_CHILDREN_KEYS", self._objects_table_name)
        async with watch_lock(txn._lock, "keys"):
            with watch("keys"):
                result = await conn.fetch(sql, oid)
        return result

    async def get_child(self, txn, parent_oid, id):
        sql = self._sql.get("GET_CHILD", self._objects_table_name)
        async with watch_lock(txn._lock, "get_child"):
            result = await self.get_one_row(txn, sql, parent_oid, id, metric="get_child")
        return result

    async def get_children(self, txn, parent_oid, ids):
        conn = await txn.get_connection()
        sql = self._sql.get("GET_CHILDREN_BATCH", self._objects_table_name)
        async with watch_lock(txn._lock, "get_children"):
            with watch("get_children"):
                return await conn.fetch(sql, parent_oid, ids)

    async def has_key(self, txn, parent_oid, id):
        sql = self._sql.get("EXIST_CHILD", self._objects_table_name)
        async with watch_lock(txn._lock, "has_key"):
            result = await self.get_one_row(txn, sql, parent_oid, id, metric="has_key")
        if result is None:
            return False
        else:
            return True

    async def len(self, txn, oid):
        conn = await txn.get_connection()
        sql = self._sql.get("NUM_CHILDREN", self._objects_table_name)
        async with watch_lock(txn._lock, "num_children"):
            with watch("num_children"):
                result = await conn.fetchval(sql, oid)
        return result

    async def items(self, txn, oid):
        conn = await txn.get_connection()
        sql = self._sql.get("GET_CHILDREN", self._objects_table_name)
        with watch("items"):
            # not going to be accurate measure but will tell you if it is abused
            async for record in conn.cursor(sql, oid):
                # locks are dangerous in cursors since comsuming code might do
                # sub-queries and they you end up with a deadlock
                yield record

    async def get_annotation(self, txn, oid, id):
        sql = self._sql.get("GET_ANNOTATION", self._objects_table_name)
        async with watch_lock(txn._lock, "load_annotation"):
            result = await self.get_one_row(txn, sql, oid, id, prepare=True, metric="load_annotation")
            if result is not None and result["parent_id"] == TRASHED_ID:
                result = None
        return result

    async def get_annotation_keys(self, txn, oid):
        conn = await txn.get_connection()
        sql = self._sql.get("GET_ANNOTATIONS_KEYS", self._objects_table_name)
        async with watch_lock(txn._lock, "load_annotation_keys"):
            with watch("load_annotation_keys"):
                result = await conn.fetch(sql, oid)
        items = []
        for item in result:
            if item["parent_id"] != TRASHED_ID:
                items.append(item)
        return items

    async def write_blob_chunk(self, txn, bid, oid, chunk_index, data):
        sql = self._sql.get("HAS_OBJECT", self._objects_table_name)
        async with watch_lock(txn._lock, "has_object"):
            result = await self.get_one_row(txn, sql, oid, metric="has_object")
        if result is None:
            # check if we have a referenced ob, could be new and not in db yet.
            # if so, create a stub for it here...
            conn = await txn.get_connection()
            async with watch_lock(txn._lock, "store_blob_stub"):
                with watch("store_blob_stub"):
                    await conn.execute(
                        f"""INSERT INTO {self._objects_table_name}
    (zoid, tid, state_size, part, resource, type)
    VALUES ($1::varchar({MAX_UID_LENGTH}), -1, 0, 0, TRUE, 'stub')""",
                        oid,
                    )
        conn = await txn.get_connection()
        sql = self._sql.get("INSERT_BLOB_CHUNK", self._blobs_table_name)
        async with watch_lock(txn._lock, "store_blob_chunk"):
            with watch("store_blob_chunk"):
                return await conn.execute(sql, bid, oid, chunk_index, data)

    async def read_blob_chunk(self, txn, bid, chunk=0):
        sql = self._sql.get("READ_BLOB_CHUNK", self._blobs_table_name)
        async with watch_lock(txn._lock, "load_blob_chunk"):
            return await self.get_one_row(txn, sql, bid, chunk, metric="load_blob_chunk")

    async def read_blob_chunks(self, txn, bid):
        conn = await txn.get_connection()
        with watch("read_blob_chunks"):
            # again, not accurate through an iterator
            async for record in conn.cursor(bid):
                # locks are dangerous in cursors since comsuming code might do
                # sub-queries and they you end up with a deadlock
                yield record

    async def del_blob(self, txn, bid):
        conn = await txn.get_connection()
        sql = self._sql.get("DELETE_BLOB", self._blobs_table_name)
        async with watch_lock(txn._lock, "delete_blob_chunk"):
            with watch("delete_blob_chunk"):
                await conn.execute(sql, bid)

    async def get_total_number_of_objects(self, txn):
        conn = await txn.get_connection()
        sql = self._sql.get("NUM_ROWS", self._objects_table_name)
        async with watch_lock(txn._lock, "total_objects"):
            with watch("total_objects"):
                result = await conn.fetchval(sql)
        return result

    async def get_total_number_of_resources(self, txn):
        conn = await txn.get_connection()
        sql = self._sql.get("NUM_RESOURCES", self._objects_table_name)
        async with watch_lock(txn._lock, "total_resources"):
            with watch("total_resources"):
                result = await conn.fetchval(sql)
        return result

    async def get_total_resources_of_type(self, txn, type_):
        conn = await txn.get_connection()
        sql = self._sql.get("NUM_RESOURCES_BY_TYPE", self._objects_table_name)
        async with watch_lock(txn._lock, "total_objects_by_type"):
            with watch("total_objects_by_type"):
                result = await conn.fetchval(sql, type_)
        return result

    # Massive treatment without security
    async def _get_page_resources_of_type(self, txn, type_, page, page_size):
        conn = await txn.get_connection()
        async with txn._lock:
            keys = []
            sql = self._sql.get("RESOURCES_BY_TYPE", self._objects_table_name)
            for record in await conn.fetch(sql, type_, page_size, (page - 1) * page_size):
                keys.append(record)
            return keys
