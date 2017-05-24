from guillotina.db.utils import lock_object
from guillotina.db.utils import unlock_object
from guillotina.tests import mocks
from guillotina.tests import utils

import asyncio


def _make_strategy():
    storage = mocks.MockStorage(transaction_strategy='lock')
    trns = mocks.MockTransaction(mocks.MockTransactionManager(storage=storage))
    return trns._strategy


async def test_locked_object_is_unlocked_tpc_finish(dummy_guillotina, etcd):
    strategy = _make_strategy()
    ob = utils.create_content()
    await strategy.lock(ob)
    assert ob.__locked__

    await strategy.tpc_finish()
    assert not ob.__locked__


async def test_register_lock_and_unlock(dummy_guillotina, etcd):
    strategy = _make_strategy()
    ob = utils.create_content()
    ob._p_jar = strategy._transaction
    await lock_object(ob)
    assert ob.__locked__
    assert ob._p_oid in strategy._transaction.modified

    await unlock_object(ob)
    assert not ob.__locked__


async def test_wait_for_lock(dummy_guillotina, etcd):
    strategy = _make_strategy()
    ob1 = utils.create_content()
    ob2 = utils.create_content()
    ob2._p_oid = ob1._p_oid
    await strategy.lock(ob1)

    result = []

    async def work_on_object_1():
        await asyncio.sleep(0.05)
        result.append(1)
        await strategy.unlock(ob1)

    async def attempt_to_lock_object_2():
        await strategy.lock(ob2)
        # should wait for object 1 to get unlocked
        result.append(2)

    await asyncio.gather(attempt_to_lock_object_2(), work_on_object_1())

    assert result == [1, 2]
