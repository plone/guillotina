from guillotina.db.transaction import Transaction
from guillotina.tests import mocks
from guillotina.tests import utils
from guillotina.transactions import managed_transaction


async def test_no_tid_created_for_reads(dummy_request, loop):
    dummy_request._db_write_enabled = False
    tm = mocks.MockTransactionManager()
    trns = Transaction(tm, dummy_request, loop=loop)
    await trns.tpc_begin()
    assert trns._tid is None


async def test_tid_created_for_writes(dummy_request, loop):
    dummy_request._db_write_enabled = True
    tm = mocks.MockTransactionManager()
    trns = Transaction(tm, dummy_request, loop=loop)
    await trns.tpc_begin()
    assert trns._tid is 1


async def test_managed_transaction_with_adoption(container_requester):
    async with container_requester as requester:
        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)
        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            container.title = 'changed title'
            container._p_register()

            assert container._p_oid in container._p_jar.modified

            # nest it with adoption
            async with managed_transaction(request=request, adopt_parent_txn=True):
                # this should commit, take on parent txn for container
                pass

            # no longer modified, adopted in previous txn
            assert container._p_oid not in container._p_jar.modified

        # finally, retrieve it again and make sure it's updated
        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            assert container.title == 'changed title'
