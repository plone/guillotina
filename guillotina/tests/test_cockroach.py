from guillotina.content import Folder
from guillotina.db.transaction_manager import TransactionManager
from guillotina.exceptions import ConflictError
from guillotina.tests.utils import create_content
from unittest import mock

import asyncio
import asyncpg
import os
import pytest


pytestmark = pytest.mark.skipif('USE_COCKROACH' not in os.environ,
                                reason="These tests are only for cockroach")


async def test_creates_vacuum_task(cockroach_storage):
    async with cockroach_storage as storage:
        assert storage._vacuum is not None
        assert storage._vacuum_task is not None


async def test_vacuum_cleans_orphaned_content(cockroach_storage, dummy_request):
    request = dummy_request  # noqa
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

        folder1._p_jar = txn
        txn.delete(folder1)

        await tm.commit(txn=txn)
        while storage._vacuum._queue.qsize() > 0 or storage._vacuum.active:
            await asyncio.sleep(0.1)

        txn = await tm.begin()
        with pytest.raises(KeyError):
            await txn.get(folder1._p_oid)
            await tm.abort(txn=txn)

        with pytest.raises(KeyError):
            # dangling...
            await txn.get(item._p_oid)
            await tm.abort(txn=txn)

        with pytest.raises(KeyError):
            # dangling...
            await txn.get(folder2._p_oid)
            await tm.abort(txn=txn)

        await tm.abort(txn=txn)


async def test_handle_serialization_error(cockroach_storage, dummy_request):
    request = dummy_request  # noqa
    async with cockroach_storage as storage:
        tm = TransactionManager(storage)
        txn = await tm.begin()
        folder1 = create_content()
        txn.register(folder1)
        await tm.commit(txn=txn)
        txn = await tm.begin()

        with mock.patch('asyncpg.prepared_stmt.PreparedStatement._PreparedStatement__bind_execute') as exe_mock:  # noqa
            exc = asyncpg.exceptions.SerializationError(
                'restart transaction: HandledRetryableTxnError: '
                'ReadWithinUncertaintyIntervalError: read at time '
                '1511374585.730535846,0 encountered')
            exc.sqlstate = '40001'
            exe_mock.side_effect = exc
            with pytest.raises(ConflictError):
                await txn.get(folder1._p_oid)
        await tm.abort(txn=txn)


async def test_deleting_parent_deletes_children(cockroach_storage, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    async with cockroach_storage as storage:
        tm = TransactionManager(storage)
        txn = await tm.begin()

        folder = create_content(Folder, 'Folder')
        txn.register(folder)
        ob = create_content()
        await folder.async_set('foobar', ob)

        assert len(txn.modified) == 2

        await tm.commit(txn=txn)
        txn = await tm.begin()

        ob2 = await txn.get(ob._p_oid)
        folder2 = await txn.get(folder._p_oid)

        assert ob2._p_oid == ob._p_oid
        assert folder2._p_oid == folder._p_oid

        # delete parent, children should be gone...
        txn.delete(folder2)
        assert len(txn.deleted) == 1
        await tm.commit(txn=txn)

        # give delete task a chance to execute
        await asyncio.sleep(0.1)

        txn = await tm.begin()

        with pytest.raises(KeyError):
            await txn.get(ob._p_oid)
        with pytest.raises(KeyError):
            await txn.get(folder._p_oid)

        await tm.abort(txn=txn)
