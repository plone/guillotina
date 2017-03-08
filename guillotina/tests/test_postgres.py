from guillotina.db import ROOT_ID
from guillotina.db.db import Root
from guillotina.db.interfaces import IWriter
from guillotina.db.reader import reader
from guillotina.db.storage import APgStorage
from guillotina.db.dummy import DummyStorage
from guillotina.db.transaction import Transaction
from guillotina.db.transaction_manager import TransactionManager

import pytest


@pytest.mark.asyncio
async def test_read_nothing(postgres):
    """Low level test checks that root is not there"""
    dsn = "postgres://guillotina:test@localhost:5432/guillotina"
    partition_object = "guillotina.db.interfaces.IPartition"
    aps = APgStorage(
        dsn=dsn, partition=partition_object, name='db')
    await aps.initialize()
    conn = await aps.open()
    tm = TransactionManager(aps)
    txn = Transaction(tm)
    await txn.tpc_begin(conn)
    lasttid = await aps.last_transaction(txn)
    with pytest.raises(KeyError):
        await aps.load(txn, ROOT_ID)
    await aps.abort(txn)
    await aps.close(txn._db_conn)
    await aps.remove()
    assert lasttid == 0


@pytest.mark.asyncio
async def test_read_something(postgres, guillotina_main):
    """Low level test checks that root is there"""
    dsn = "postgres://guillotina:test@localhost:5432/guillotina"
    partition_object = "guillotina.db.interfaces.IPartition"
    aps = APgStorage(
        dsn=dsn, partition=partition_object, name='db')
    await aps.initialize()
    conn = await aps.open()
    tm = TransactionManager(aps)
    txn = Transaction(tm)
    await txn.tpc_begin(conn)
    lasttid = await aps.last_transaction(txn)
    await aps.load(txn, ROOT_ID)
    await aps.abort(txn)
    await aps.close(txn._db_conn)
    await aps.remove()
    assert lasttid == 1


@pytest.mark.asyncio
async def test_pg_txn(postgres, guillotina_main):
    """Test a low level transaction"""
    dsn = "postgres://guillotina:test@localhost:5432/guillotina"
    partition_object = "guillotina.db.interfaces.IPartition"
    aps = APgStorage(
        dsn=dsn, partition=partition_object, name='db')
    await aps.initialize()
    conn = await aps.open()
    obj = Root()
    writer = IWriter(obj)
    tm = TransactionManager(DummyStorage())
    txn = Transaction(tm)
    await aps.tpc_begin(txn, conn)
    await aps.precommit(txn)
    await aps.store(ROOT_ID, 0, writer, obj, txn)
    await aps.tpc_vote(txn)
    await aps.tpc_finish(txn)
    await aps.close(conn)

    tm = TransactionManager(DummyStorage())
    txn = Transaction(tm)
    await aps.tpc_begin(txn, conn)
    result = await aps.load(txn, ROOT_ID)
    await aps.abort(txn)
    await aps.close(txn._db_conn)
    obj2 = reader(result)
    # XXX causing it to hang here?
    # await aps.remove()
    assert obj.__name__ == obj2.__name__
