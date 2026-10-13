import asyncio
import hashlib
from contextlib import asynccontextmanager

import asyncpg

from guillotina import task_vars
from guillotina.exceptions import ObjectLockedError, ReadOnlyError, TransactionNotFound


def _oid_lock_key(oid: str) -> int:
    digest = hashlib.blake2b(oid.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=True)


@asynccontextmanager
async def lock_object_for_write(oid: str, *, retries: int = 3, delay: float = 0.05):
    """
    Acquire a transaction-scoped advisory lock for a Guillotina object.
    Must be used inside an active transaction.
    """
    txn = task_vars.txn.get()
    if txn is None:
        raise TransactionNotFound()
    if getattr(txn, "read_only", False):
        raise ReadOnlyError()

    storage = txn.storage
    if getattr(txn, "_db_txn", None) is None:
        await storage.start_transaction(txn)

    if retries < 1:
        retries = 1

    key = _oid_lock_key(oid)
    async with storage.acquire(txn, "object_lock") as conn:
        for attempt in range(1, retries + 1):
            try:
                locked = await conn.fetchval("SELECT pg_try_advisory_xact_lock($1);", key)
            except asyncpg.exceptions.UndefinedFunctionError as ex:
                raise NotImplementedError("Object locks require PostgreSQL advisory locks") from ex
            if locked:
                break
            if attempt < retries and delay > 0:
                await asyncio.sleep(delay)
        else:
            raise ObjectLockedError(oid, retries)

    try:
        yield
    finally:
        # xact lock is released on commit/rollback
        pass
