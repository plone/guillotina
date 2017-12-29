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
    request = get_current_request()
    txn = get_transaction(request)
    tm = get_tm(request)
    await tm.abort(txn=txn)

    tm._storage._transaction_strategy = strategy

    print(f'Test content create with {strategy} strategy')
    start = time.time()
    for _ in range(ITERATIONS):
        txn = await tm.begin(request=request)
        id_ = uuid.uuid4().hex
        await create_content_in_container(container, 'Item', id_)
        await tm.commit(txn=txn)
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')

    print(f'Test large number create with {strategy} strategy')
    start = time.time()
    txn = await tm.begin(request=request)
    for _ in range(ITERATIONS):
        id_ = uuid.uuid4().hex
        await create_content_in_container(container, 'Item', id_)
    await tm.commit(txn=txn)
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds\n')


async def read_runner(container, strategy):
    request = get_current_request()
    txn = get_transaction(request)
    tm = get_tm(request)
    id_ = uuid.uuid4().hex
    await tm.abort(txn=txn)
    txn = await tm.begin(request=request)
    ob = await create_content_in_container(container, 'Item', id_)
    await tm.commit(txn=txn)

    tm._storage._transaction_strategy = strategy

    print(f'Test content read with {strategy} strategy')
    start = time.time()
    for _ in range(ITERATIONS):
        txn = await tm.begin(request=request)
        assert await txn.get(ob._p_oid) is not None
        await tm.commit(txn=txn)
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')

    print(f'Test large content read with {strategy} strategy')
    start = time.time()
    txn = await tm.begin(request=request)
    for _ in range(ITERATIONS):
        assert await txn.get(ob._p_oid) is not None
    await tm.commit(txn=txn)
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds\n')


async def runner(container, strategy):
    await write_runner(container, strategy)
    await read_runner(container, strategy)


async def run(container):
    await runner(container, 'resolve')
    await runner(container, 'resolve_readcommitted')
    await runner(container, 'none')
    await runner(container, 'tidonly')
    await runner(container, 'simple')
    await runner(container, 'dbresolve')
    await runner(container, 'dbresolve_readcommitted')
