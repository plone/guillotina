from guillotina.content import create_content_in_container
from guillotina.db import ROOT_ID
from guillotina.db.transaction import Transaction
from guillotina.tests import mocks
from guillotina.transactions import transaction
from guillotina.utils import get_object_by_uid


async def test_no_tid_created_for_reads(dummy_request, loop):
    tm = mocks.MockTransactionManager()
    trns = Transaction(tm, loop=loop, read_only=True)
    await trns.tpc_begin()
    assert trns._tid is None


async def test_tid_created_for_writes(dummy_request, loop):
    tm = mocks.MockTransactionManager()
    trns = Transaction(tm, loop=loop)
    await trns.tpc_begin()
    assert trns._tid == 1


async def test_managed_transaction_with_adoption(container_requester):
    async with container_requester as requester:
        async with transaction(db=requester.db, abort_when_done=True) as txn:
            root = await txn.get(ROOT_ID)
            container = await root.async_get("guillotina")
            container.title = "changed title"
            container.register()

            assert container.__uuid__ in txn.modified

            # nest it with adoption
            async with transaction(adopt_parent_txn=True):
                # this should commit, take on parent txn for container
                pass

            # no longer modified, adopted in previous txn
            assert container.__uuid__ not in txn.modified

        # finally, retrieve it again and make sure it's updated
        async with transaction(abort_when_done=True):
            container = await root.async_get("guillotina")
            assert container.title == "changed title"


async def test_managed_transaction_works_with_parent_txn_adoption(container_requester):
    async with container_requester as requester:
        async with transaction(db=requester.db) as txn:
            # create some content
            root = await txn.get(ROOT_ID)
            container = await root.async_get("guillotina")
            await create_content_in_container(
                container, "Item", "foobar", check_security=False, __uuid__="foobar"
            )

        async with transaction(db=requester.db) as txn:
            root = await txn.get(ROOT_ID)
            container = await root.async_get("guillotina")

            # nest it with adoption
            async with transaction(adopt_parent_txn=True) as txn:
                ob = await get_object_by_uid("foobar", txn)
                txn.delete(ob)

        # finally, retrieve it again and make sure it's updated
        async with transaction(db=requester.db) as txn:
            root = await txn.get(ROOT_ID)
            container = await root.async_get("guillotina")
            assert await container.async_get("foobar") is None
