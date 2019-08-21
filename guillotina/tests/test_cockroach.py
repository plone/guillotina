from guillotina.component import get_adapter
from guillotina.content import Folder
from guillotina.db.interfaces import IVacuumProvider
from guillotina.db.transaction_manager import TransactionManager
from guillotina.tests.utils import create_content

import asyncio
import os
import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("DATABASE") != "cockroachdb", reason="These tests are only for cockroach"
)


async def test_creates_vacuum_task(cockroach_storage):
    async with cockroach_storage as storage:
        assert storage.connection_manager._vacuum is not None
        assert storage.connection_manager._vacuum_task is not None


async def test_vacuum_cleans_orphaned_content(cockroach_storage):
    async with cockroach_storage as storage:
        tm = TransactionManager(storage)
        txn = await tm.begin()

        folder1 = create_content()
        txn.register(folder1)
        folder2 = create_content()
        folder2.__parent__ = folder1
        txn.register(folder2)
        item = create_content()
        item.__parent__ = folder2
        txn.register(item)

        await tm.commit(txn=txn)
        txn = await tm.begin()

        folder1.__txn__ = txn
        txn.delete(folder1)

        await tm.commit(txn=txn)

        vacuumer = get_adapter(storage, IVacuumProvider)
        await vacuumer()

        txn = await tm.begin()
        with pytest.raises(KeyError):
            await txn.get(folder1.__uuid__)
            await tm.abort(txn=txn)

        with pytest.raises(KeyError):
            # dangling...
            await txn.get(item.__uuid__)
            await tm.abort(txn=txn)

        with pytest.raises(KeyError):
            # dangling...
            await txn.get(folder2.__uuid__)
            await tm.abort(txn=txn)

        await tm.abort(txn=txn)


async def test_deleting_parent_deletes_children(cockroach_storage):
    async with cockroach_storage as storage:
        tm = TransactionManager(storage)
        txn = await tm.begin()

        folder = create_content(Folder, "Folder")
        txn.register(folder)
        ob = create_content()
        await folder.async_set("foobar", ob)

        assert len(txn.modified) == 2

        await tm.commit(txn=txn)
        txn = await tm.begin()

        ob2 = await txn.get(ob.__uuid__)
        folder2 = await txn.get(folder.__uuid__)

        assert ob2.__uuid__ == ob.__uuid__
        assert folder2.__uuid__ == folder.__uuid__

        # delete parent, children should be gone...
        txn.delete(folder2)
        assert len(txn.deleted) == 1
        await tm.commit(txn=txn)

        # give delete task a chance to execute
        await asyncio.sleep(0.1)

        txn = await tm.begin()

        with pytest.raises(KeyError):
            await txn.get(ob.__uuid__)
        with pytest.raises(KeyError):
            await txn.get(folder.__uuid__)

        await tm.abort(txn=txn)
