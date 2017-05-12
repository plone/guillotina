from guillotina.behaviors.dublincore import IDublinCore
from guillotina.content import Folder
from guillotina.db.storages.pg import PostgresqlStorage
from guillotina.db.transaction_manager import TransactionManager
from guillotina.exceptions import ConflictError
from guillotina.interfaces import IResource
from guillotina.tests.utils import create_content

import asyncio
import concurrent
import pytest


async def cleanup(aps):
    conn = await aps.open()
    txn = conn.transaction()
    await txn.start()
    await conn.execute("DROP TABLE IF EXISTS objects;")
    await conn.execute("DROP TABLE IF EXISTS blobs;")
    await conn.execute("ALTER SEQUENCE tid_sequence RESTART WITH 1")
    await txn.commit()
    await aps._pool.release(conn)


async def get_aps(strategy='resolve', pool_size=15):
    dsn = "postgres://postgres:@localhost:5432/guillotina"
    partition_object = "guillotina.db.interfaces.IPartition"
    aps = PostgresqlStorage(
        dsn=dsn, partition=partition_object, name='db',
        transaction_strategy=strategy, pool_size=pool_size,
        conn_acquire_timeout=0.1)
    await aps.initialize()
    return aps


async def test_read_obs(postgres, dummy_request):
    """Low level test checks that root is not there"""
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm = TransactionManager(aps)
    txn = await tm.begin()

    ob = create_content()
    txn.register(ob)

    assert len(txn.modified) == 1

    await tm.commit(txn=txn)

    txn = await tm.begin()

    ob2 = await txn.get(ob._p_oid)

    assert ob2._p_oid == ob._p_oid
    await tm.commit(txn=txn)

    await aps.remove()
    await cleanup(aps)


async def test_deleting_parent_deletes_children(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm = TransactionManager(aps)
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
    txn = await tm.begin()

    with pytest.raises(KeyError):
        await txn.get(ob._p_oid)
    with pytest.raises(KeyError):
        await txn.get(folder._p_oid)

    await tm.abort(txn=txn)

    await aps.remove()
    await cleanup(aps)


async def test_create_blob(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm = TransactionManager(aps)
    txn = await tm.begin()

    ob = create_content()
    txn.register(ob)

    await txn.write_blob_chunk('X' * 32, ob._p_oid, 0, b'foobar')

    await tm.commit(txn=txn)
    txn = await tm.begin()

    blob_record = await txn.read_blob_chunk('X' * 32, 0)
    assert blob_record['data'] == b'foobar'

    # also get data from ob that started as a stub...
    ob2 = await txn.get(ob._p_oid)
    assert ob2.type_name == 'Item'
    assert ob2.id == 'foobar'

    await tm.abort(txn=txn)

    await aps.remove()
    await cleanup(aps)


async def test_delete_resource_deletes_blob(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm = TransactionManager(aps)
    txn = await tm.begin()

    ob = create_content()
    txn.register(ob)

    await txn.write_blob_chunk('X' * 32, ob._p_oid, 0, b'foobar')

    await tm.commit(txn=txn)
    txn = await tm.begin()

    ob = await txn.get(ob._p_oid)
    txn.delete(ob)

    await tm.commit(txn=txn)
    txn = await tm.begin()

    assert await txn.read_blob_chunk('X' * 32, 0) is None

    with pytest.raises(KeyError):
        await txn.get(ob._p_oid)

    await tm.abort(txn=txn)
    await aps.remove()
    await cleanup(aps)

async def test_should_raise_conflict_error_when_editing_diff_data_with_resolve_strat(
        postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps('resolve')
    tm = TransactionManager(aps)

    # create object first, commit it...
    txn = await tm.begin()

    ob = create_content()
    ob.title = 'foobar'
    ob.description = 'foobar'
    txn.register(ob)

    await tm.commit(txn=txn)

    # 1 started before 2
    txn1 = await tm.begin()
    txn2 = await tm.begin()

    ob1 = await txn1.get(ob._p_oid)
    ob2 = await txn2.get(ob._p_oid)
    ob1.title = 'foobar1'
    ob2.description = 'foobar2'

    txn1.register(ob1)
    txn2.register(ob2)

    # commit 2 before 1
    await tm.commit(txn=txn2)
    with pytest.raises(ConflictError):
        await tm.commit(txn=txn1)

    await aps.remove()
    await cleanup(aps)


async def test_should_resolve_conflict_error(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm = TransactionManager(aps)

    # create object first, commit it...
    txn = await tm.begin()

    ob1 = create_content()
    ob2 = create_content()
    txn.register(ob1)
    txn.register(ob2)

    await tm.commit(txn=txn)

    # 1 started before 2
    txn1 = await tm.begin()
    txn2 = await tm.begin()

    ob1 = await txn1.get(ob1._p_oid)
    ob2 = await txn2.get(ob2._p_oid)

    txn1.register(ob1)
    txn2.register(ob2)

    # commit 2 before 1
    await tm.commit(txn=txn2)
    # XXX should not raise conflict error
    await tm.commit(txn=txn1)

    await aps.remove()
    await cleanup(aps)


async def test_should_not_resolve_conflict_error_with_simple_strat(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps('simple')
    tm = TransactionManager(aps)

    # create object first, commit it...
    txn = await tm.begin()

    ob1 = create_content()
    ob2 = create_content()
    txn.register(ob1)
    txn.register(ob2)

    await tm.commit(txn=txn)

    # 1 started before 2
    txn1 = await tm.begin()
    txn2 = await tm.begin()

    ob1 = await txn1.get(ob1._p_oid)
    ob2 = await txn2.get(ob2._p_oid)

    txn1.register(ob1)
    txn2.register(ob2)

    # commit 2 before 1
    await tm.commit(txn=txn2)
    # XXX should not raise conflict error
    with pytest.raises(ConflictError):
        await tm.commit(txn=txn1)

    await aps.remove()
    await cleanup(aps)


async def test_none_strat_allows_trans_commits(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps('none')
    tm = TransactionManager(aps)

    # create object first, commit it...
    txn = await tm.begin()

    ob1 = create_content()
    txn.register(ob1)

    await tm.commit(txn=txn)

    txn1 = await tm.begin()
    txn2 = await tm.begin()
    ob1 = await txn1.get(ob1._p_oid)
    ob2 = await txn2.get(ob1._p_oid)
    ob1.title = 'foobar1'
    ob2.title = 'foobar2'
    txn1.register(ob1)
    txn2.register(ob2)

    await tm.commit(txn=txn2)
    await tm.commit(txn=txn1)

    txn = await tm.begin()
    ob1 = await txn.get(ob1._p_oid)
    assert ob1.title == 'foobar1'

    await tm.abort(txn=txn)

    await aps.remove()
    await cleanup(aps)


async def test_count_total_objects(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm = TransactionManager(aps)

    # create object first, commit it...
    txn = await tm.begin()

    ob = create_content()
    txn.register(ob)

    await tm.commit(txn=txn)
    txn = await tm.begin()

    assert await txn.get_total_number_of_objects() == 1
    assert await txn.get_total_number_of_resources() == 1

    await tm.abort(txn=txn)

    await aps.remove()
    await cleanup(aps)


async def test_using_gather_with_queries_before_prepare(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm = TransactionManager(aps)

    # create object first, commit it...
    txn = await tm.begin()

    ob1 = create_content()
    txn.register(ob1)

    await tm.commit(txn=txn)

    txn = await tm.begin()

    async def get_ob():
        await txn.get(ob1._p_oid)

    # before we introduced locking on the connection, this would error
    await asyncio.gather(get_ob(), get_ob(), get_ob(), get_ob(), get_ob())

    await tm.abort(txn=txn)

    await aps.remove()
    await cleanup(aps)


async def test_using_gather_with_queries_after_prepare(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm = TransactionManager(aps)

    # create object first, commit it...
    txn = await tm.begin()

    ob1 = create_content()
    txn.register(ob1)

    await tm.commit(txn=txn)

    txn = await tm.begin()

    async def get_ob():
        await txn.get(ob1._p_oid)

    # one initial call should load prepared statement
    await txn.get(ob1._p_oid)

    # before we introduction locking on the connection, this would error
    await asyncio.gather(get_ob(), get_ob(), get_ob(), get_ob(), get_ob())

    await tm.abort(txn=txn)

    await aps.remove()
    await cleanup(aps)


async def test_exhausting_pool_size(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    # base aps uses 1 connection from the pool for starting transactions
    aps = await get_aps(pool_size=2)
    tm = TransactionManager(aps)
    txn = await tm.begin()

    with pytest.raises(concurrent.futures._base.TimeoutError):
        # should throw an error because we've run out of connections in pool
        await tm.begin()

    await tm.abort(txn=txn)

    await aps.remove()
    await cleanup(aps)


async def test_mismatched_tid_causes_conflict_error(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    # base aps uses 1 connection from the pool for starting transactions
    aps = await get_aps()
    tm = TransactionManager(aps)
    txn = await tm.begin()

    ob1 = create_content()
    txn.register(ob1)
    await tm.commit(txn=txn)

    txn = await tm.begin()
    ob1 = await txn.get(ob1._p_oid)
    # modify p_serial, try committing, should raise conflict error
    ob1._p_serial = 3242432
    txn.register(ob1)

    with pytest.raises(ConflictError):
        await tm.commit(txn=txn)

    await aps.remove()
    await cleanup(aps)
