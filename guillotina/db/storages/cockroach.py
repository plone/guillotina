from guillotina import glogging
from guillotina.db.interfaces import ICockroachStorage
from guillotina.db.storages import pg
from guillotina.db.storages.utils import register_sql
from guillotina.db.uid import MAX_UID_LENGTH
from guillotina.exceptions import ConflictError
from guillotina.exceptions import ConflictIdOnContainer
from guillotina.exceptions import RequestNotFound
from guillotina.exceptions import RestartCommit
from guillotina.exceptions import TIDConflictError
from guillotina.utils import get_current_request
from zope.interface import implementer

import asyncpg


logger = glogging.getLogger("guillotina")

# upsert without checking matching tids on updated object
register_sql(
    "CR_NAIVE_UPSERT",
    f"""
INSERT INTO {{table_name}}
(zoid, tid, state_size, part, resource, of, otid, parent_id, id, type, state)
VALUES ($1::varchar({MAX_UID_LENGTH}), $2::int, $3::int, $4::int, $5::boolean,
        $6::varchar({MAX_UID_LENGTH}), $7::int, $8::varchar({MAX_UID_LENGTH}),
        $9::text, $10::text, $11::bytea)
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
RETURNING NOTHING""",
)


# update without checking matching tids on updated object
register_sql(
    "CR_UPDATE",
    f"""
UPDATE {{table_name}}
SET
    tid = $2::int,
    state_size = $3::int,
    part = $4::int,
    resource = $5::boolean,
    of = $6::varchar({MAX_UID_LENGTH}),
    otid = $7::int,
    parent_id = $8::varchar({MAX_UID_LENGTH}),
    id = $9::text,
    type = $10::text,
    state = $11::bytea
WHERE
    zoid = $1::varchar({MAX_UID_LENGTH})
    AND tid = $7::int
RETURNING tid, otid""",
)


class CockroachDBTransaction:
    """
    Custom transaction object to work with cockroachdb so we can...
    1. restart commits when cockroach throws a 40001 error
    2. retry transctions with custom priorities
    """

    commit_statement = """RELEASE SAVEPOINT cockroach_restart;
COMMIT;"""

    def __init__(self, txn):
        self._txn = txn
        self._conn = txn._db_conn
        self._storage = txn._manager._storage
        self._status = "none"
        self._priority = "LOW"
        try:
            request = get_current_request()
            attempts = getattr(request, "_retry_attempt", 0)
            if attempts == 1:
                self._priority = "NORMAL"
            elif attempts > 1:
                self._priority = "HIGH"
        except RequestNotFound:
            pass

    async def start(self):
        assert self._status in ("none",)
        await self._conn.execute(
            f"""BEGIN PRIORITY {self._priority};
SAVEPOINT cockroach_restart;"""
        )
        self._status = "started"

    async def commit(self):
        assert self._status in ("started",)
        try:
            await self._conn.execute(self.commit_statement)
        except asyncpg.exceptions.UniqueViolationError as ex:
            if "duplicate key value (parent_id,id)" in ex.message:
                raise ConflictIdOnContainer(ex)
            raise
        self._status = "committed"

    async def restart(self):
        await self._conn.execute("ROLLBACK TO SAVEPOINT COCKROACH_RESTART")

    async def rollback(self):
        assert self._status in ("started",)
        try:
            await self._conn.execute("ROLLBACK;")
        except asyncpg.exceptions.InternalServerError:
            # already aborted...
            pass
        self._status = "rolledback"


class CRConnectionManager(pg.PGConnectionManager):
    _next_tid_sql = "SELECT unique_rowid()"
    # cr does not support this type of txn
    _max_tid_sql = "SELECT 1;"


@implementer(ICockroachStorage)
class CockroachStorage(pg.PostgresqlStorage):
    """
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
    """

    _db_transaction_factory = CockroachDBTransaction
    _connection_manager_class = CRConnectionManager
    _vacuum = _vacuum_task = None
    _unique_constraints = [
        """CREATE UNIQUE INDEX {constraint_name}_parent_id_id_key
           ON {objects_table_name} (parent_id, id)""",
        # not supported yet
        #                        WHERE parent_id != '{TRASHED_ID}'"""
        """CREATE UNIQUE INDEX CONCURRENTLY {constraint_name}_annotations_unique ON {objects_table_name} (of, id);""",
    ]

    def __init__(self, *args, **kwargs):
        transaction_strategy = kwargs.get("transaction_strategy", "dbresolve_readcommitted")
        if transaction_strategy not in ("none", "tidonly", "dbresolve", "dbresolve_readcommitted"):
            logger.warning(
                f"Unsupported transaction strategy specified for "
                f"cockroachdb({transaction_strategy}). "
                f"Forcing to `dbresolve_readcommitted` strategy"
            )
            transaction_strategy = "dbresolve_readcommitted"
        kwargs["transaction_strategy"] = transaction_strategy
        super().__init__(*args, **kwargs)

    async def get_current_tid(self, txn):  # pragma: no cover
        raise Exception("cockroach does not support voting")

    async def has_unique_constraint(self, conn):
        try:
            for result in await conn.fetch("""SHOW CONSTRAINTS FROM {};""".format(self._objects_table_name)):
                result = dict(result)
                c_name = result.get("Name", result.get("constraint_name"))
                if c_name == "{}_parent_id_id_key".format(self._objects_table_name):
                    return True
        except asyncpg.exceptions.UndefinedTableError:
            pass
        except Exception:
            logger.warning("Unknown error attempting to detect constraints installed.", exc_info=True)
        return False

    async def store(self, oid, old_serial, writer, obj, txn):
        assert oid is not None

        pickled = writer.serialize()  # This calls __getstate__ of obj
        if len(pickled) >= self._large_record_size:
            logger.warning(f"Large object {obj.__class__}: {len(pickled)}")
        part = writer.part
        if part is None:
            part = 0

        statement_sql = self._sql.get("CR_NAIVE_UPSERT", self._objects_table_name)
        update = False
        if not obj.__new_marker__ and obj.__serial__ is not None:
            # we should be confident this is an object update
            statement_sql = self._sql.get("CR_UPDATE", self._objects_table_name)
            update = True

        conn = await txn.get_connection()
        async with txn._lock:
            try:
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
                    pickled,  # Pickle state)
                )
            except asyncpg.exceptions.UniqueViolationError as ex:
                if "duplicate key value (parent_id,id)" in ex.detail:
                    raise ConflictIdOnContainer(ex)
                raise
            except asyncpg.exceptions._base.InterfaceError as ex:
                if "another operation is in progress" in ex.args[0]:
                    raise ConflictError(
                        f"asyncpg error, another operation in progress.", oid, txn, old_serial, writer
                    )
                raise
            if update and len(result) != 1:
                # raise tid conflict error
                raise TIDConflictError(
                    f"Mismatch of tid of object being updated. This is likely "
                    f"caused by a cache invalidation race condition and should "
                    f"be an edge case. This should resolve on request retry.",
                    oid,
                    txn,
                    old_serial,
                    writer,
                )
        await txn._cache.store_object(obj, pickled)

    async def commit(self, transaction):
        if transaction._db_txn is not None:
            async with transaction._lock:
                try:
                    await transaction._db_txn.commit()
                except asyncpg.exceptions.SerializationError as ex:
                    if ex.sqlstate == "40001":
                        raise RestartCommit(ex.args[0])
        elif self._transaction_strategy not in ("none", "tidonly"):
            logger.info("Do not have db transaction to commit")

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
            if ex.sqlstate == "40001":
                # these are not handled with the ROLLBACK TO SAVEPOINT COCKROACH_RESTART
                # logic unfortunately; however, it does give us a chance to handle
                # it like a restart with higher priority
                raise ConflictError(ex.args[0])
        return result[0] if len(result) > 0 else None
