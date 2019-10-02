from guillotina import task_vars
from guillotina.content import create_content_in_container
from guillotina.db import ROOT_ID
from guillotina.db.transaction import Transaction
from guillotina.exceptions import TransactionClosedException
from guillotina.exceptions import TransactionNotFound
from guillotina.exceptions import TransactionObjectRegistrationMismatchException
from guillotina.tests import mocks
from guillotina.tests import utils
from guillotina.transactions import transaction
from guillotina.utils import get_database
from guillotina.utils import get_object_by_uid

import pytest


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

            assert container.__uuid__ in container.__txn__.modified

            # nest it with adoption
            async with transaction(db=requester.db, adopt_parent_txn=True):
                # this should commit, take on parent txn for container
                pass

            # no longer modified, adopted in previous txn
            assert container.__uuid__ not in container.__txn__.modified

        # finally, retrieve it again and make sure it's updated
        async with transaction(db=requester.db, abort_when_done=True):
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


async def test_txn_refresh(container_requester):
    async with container_requester as requester:
        async with transaction(db=requester.db) as txn:
            root = await txn.get(ROOT_ID)
            container1 = await root.async_get("guillotina")
            container1.title = "changed title"
            container1.register()

        async with transaction(db=requester.db) as txn:
            container2 = await root.async_get("guillotina")
            container2.title = "changed title2"
            container2.register()

        async with transaction(db=requester.db) as txn:
            assert container1.__serial__ != container2.__serial__
            assert container1.title != container2.title
            await txn.refresh(container1)
            assert container1.__serial__ == container2.__serial__
            assert container1.title == container2.title


async def test_register_with_local_txn_if_no_global(container_requester):
    async with container_requester as requester:
        db = requester.db
        tm = db.get_transaction_manager()
        txn = await tm.begin()
        root = await txn.get(ROOT_ID)
        container = await root.async_get("guillotina")
        task_vars.txn.set(None)
        container.register()
        assert await container.async_get("foobar") is None
        assert container.__uuid__ in txn.modified
        await tm.abort(txn=txn)

        with pytest.raises(TransactionClosedException):
            # when txn closed, raise exception
            container.register()

        container.__txn__ = None
        with pytest.raises(TransactionNotFound):
            # when no txn found, raise exception
            container.register()

        with pytest.raises(TransactionNotFound):
            await container.async_get("foobar")


async def test_create_txn_with_db(container_requester):
    async with container_requester as requester:
        async with requester.db.transaction() as txn:
            root = await txn.get(ROOT_ID)
            assert root is not None


async def test_register_duplicate_object_oid(guillotina_main):
    async with transaction(db=await get_database("db")) as txn:
        txn.register(utils.create_content(uid="foobar"))
        with pytest.raises(TransactionObjectRegistrationMismatchException):
            txn.register(utils.create_content(uid="foobar"))
