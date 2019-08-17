from guillotina.content import create_content_in_container
from guillotina.transactions import get_tm
from guillotina.transactions import get_transaction
from guillotina.utils import get_current_request

import time
import uuid


ITERATIONS = 100

# ----------------------------------------------------
# Measure performance of different caching strategies
#
# Lessons:
# ----------------------------------------------------


async def write_runner(container, strategy):
    txn = get_transaction()
    tm = get_tm()
    await tm.abort(txn=txn)

    tm._storage._transaction_strategy = strategy

    print(f"Test content create with {strategy} strategy")
    start = time.time()
    for _ in range(ITERATIONS):
        txn = await tm.begin()
        id_ = uuid.uuid4().hex
        await create_content_in_container(container, "Item", id_)
        await tm.commit(txn=txn)
    end = time.time()
    print(f"Done with {ITERATIONS} in {end - start} seconds")

    print(f"Test large number create with {strategy} strategy")
    start = time.time()
    txn = await tm.begin()
    for _ in range(ITERATIONS):
        id_ = uuid.uuid4().hex
        await create_content_in_container(container, "Item", id_)
    await tm.commit(txn=txn)
    end = time.time()
    print(f"Done with {ITERATIONS} in {end - start} seconds\n")


async def read_runner(container, strategy):
    txn = get_transaction()
    tm = get_tm()
    id_ = uuid.uuid4().hex
    await tm.abort(txn=txn)
    txn = await tm.begin()
    ob = await create_content_in_container(container, "Item", id_)
    await tm.commit(txn=txn)

    tm._storage._transaction_strategy = strategy

    print(f"Test content read with {strategy} strategy")
    start = time.time()
    for _ in range(ITERATIONS):
        txn = await tm.begin()
        assert await txn.get(ob.__uuid__) is not None
        await tm.commit(txn=txn)
    end = time.time()
    print(f"Done with {ITERATIONS} in {end - start} seconds")

    print(f"Test large content read with {strategy} strategy")
    start = time.time()
    txn = await tm.begin()
    for _ in range(ITERATIONS):
        assert await txn.get(ob.__uuid__) is not None
    await tm.commit(txn=txn)
    end = time.time()
    print(f"Done with {ITERATIONS} in {end - start} seconds\n")


async def runner(container, strategy):
    await write_runner(container, strategy)
    await read_runner(container, strategy)


async def run(container):
    await runner(container, "resolve")
    await runner(container, "resolve_readcommitted")
    await runner(container, "none")
    await runner(container, "tidonly")
    await runner(container, "simple")
    await runner(container, "dbresolve")
    await runner(container, "dbresolve_readcommitted")
