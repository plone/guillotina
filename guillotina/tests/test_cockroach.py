from guillotina.db.transaction_manager import TransactionManager
from guillotina.tests.utils import create_content

import asyncio
import os
import pytest


pytestmark = pytest.mark.skipif('USE_COCKROACH' not in os.environ,
                                reason="These tests are only for cockroach")


async def test_creates_vacuum_task(cockroach_storage):
    async with await cockroach_storage as storage:
        assert storage._vacuum is not None
        assert storage._vacuum_task is not None


async def test_vacuum_cleans_orphaned_content(cockroach_storage, dummy_request):
    request = dummy_request  # noqa
    async with await cockroach_storage as storage:
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
