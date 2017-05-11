from guillotina.db.transaction import Transaction
from guillotina.tests import mocks


async def test_no_tid_created_for_reads(dummy_request, loop):
    dummy_request._db_write_enabled = False
    tm = mocks.MockTransactionManager()
    trns = Transaction(tm, dummy_request, loop=loop)
    await trns.tpc_begin(None)
    assert trns._tid is None


async def test_tid_created_for_writes(dummy_request, loop):
    dummy_request._db_write_enabled = True
    tm = mocks.MockTransactionManager()
    trns = Transaction(tm, dummy_request, loop=loop)
    await trns.tpc_begin(None)
    assert trns._tid is 1
