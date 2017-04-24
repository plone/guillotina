from guillotina.behaviors import apply_markers
from guillotina.content import Folder
from guillotina.content import Item
from guillotina.db.storages.pg import PostgresqlStorage
from guillotina.db.transaction_manager import TransactionManager
from guillotina.exceptions import ConflictError

import pytest
import uuid


async def cleanup(aps):
    conn = await aps.open()
    txn = conn.transaction()
    await txn.start()
    await conn.execute("DROP TABLE IF EXISTS objects;")
    await conn.execute("DROP TABLE IF EXISTS blobs;")
    await conn.execute("ALTER SEQUENCE tid_seq RESTART WITH 1;")
    await txn.commit()
    await aps._pool.release(conn)


async def get_aps():
    dsn = "postgres://postgres:@localhost:5432/guillotina"
    partition_object = "guillotina.db.interfaces.IPartition"
    aps = PostgresqlStorage(
        dsn=dsn, partition=partition_object, name='db')
    await aps.initialize()
    return aps


def create_ob():
    obj = Item()
    obj.type_name = 'Item'
    obj._p_oid = uuid.uuid4().hex
    obj.__name__ = obj.id = 'foobar'
    apply_markers(obj, None)
    return obj


def create_folder():
    obj = Folder()
    obj.type_name = 'Folder'
    obj._p_oid = uuid.uuid4().hex
    obj.__name__ = obj.id = 'foobar'
    apply_markers(obj, None)
    return obj


async def test_read_obs(postgres, dummy_request):
    """Low level test checks that root is not there"""
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm = TransactionManager(aps)
    await tm.begin()
    txn = tm._txn

    ob = create_ob()
    txn.register(ob)

    assert len(txn.modified) == 1

    await tm.commit()

    await tm.begin()
    txn = tm._txn

    lasttid = await aps.last_transaction(txn)
    assert lasttid is not None

    ob2 = await txn.get(ob._p_oid)

    assert ob2._p_oid == ob._p_oid
    await tm.commit()

    await aps.remove()
    await cleanup(aps)


async def test_deleting_parent_deletes_children(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm = TransactionManager(aps)
    await tm.begin()
    txn = tm._txn

    folder = create_folder()
    txn.register(folder)
    ob = create_ob()
    await folder.async_set('foobar', ob)

    assert len(txn.modified) == 2

    await tm.commit()
    await tm.begin()
    txn = tm._txn

    ob2 = await txn.get(ob._p_oid)
    folder2 = await txn.get(folder._p_oid)

    assert ob2._p_oid == ob._p_oid
    assert folder2._p_oid == folder._p_oid

    # delete parent, children should be gone...
    txn.delete(folder2)
    assert len(txn.deleted) == 1

    await tm.commit()
    await tm.begin()
    txn = tm._txn

    with pytest.raises(KeyError):
        await txn.get(ob._p_oid)
    with pytest.raises(KeyError):
        await txn.get(folder._p_oid)

    await tm.abort()

    await aps.remove()
    await cleanup(aps)


async def test_create_blob(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm = TransactionManager(aps)
    await tm.begin()
    txn = tm._txn

    ob = create_ob()
    txn.register(ob)

    await txn.write_blob_chunk('X' * 32, ob._p_oid, 0, b'foobar')

    await tm.commit()
    await tm.begin()
    txn = tm._txn

    blob_record = await txn.read_blob_chunk('X' * 32, 0)
    assert blob_record['data'] == b'foobar'

    # also get data from ob that started as a stub...
    ob2 = await txn.get(ob._p_oid)
    assert ob2.type_name == 'Item'
    assert ob2.id == 'foobar'

    await tm.abort()

    await aps.remove()
    await cleanup(aps)


async def test_delete_resource_deletes_blob(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm = TransactionManager(aps)
    await tm.begin()
    txn = tm._txn

    ob = create_ob()
    txn.register(ob)

    await txn.write_blob_chunk('X' * 32, ob._p_oid, 0, b'foobar')

    await tm.commit()
    await tm.begin()
    txn = tm._txn

    ob = await txn.get(ob._p_oid)
    txn.delete(ob)

    await tm.commit()
    await tm.begin()
    txn = tm._txn

    assert await txn.read_blob_chunk('X' * 32, 0) is None

    with pytest.raises(KeyError):
        await txn.get(ob._p_oid)

    await tm.abort()
    await aps.remove()
    await cleanup(aps)


async def test_should_raise_conflict_error(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm1 = TransactionManager(aps)
    tm2 = TransactionManager(aps)

    # create object first, commit it...
    await tm1.begin()
    txn = tm1._txn

    ob = create_ob()
    txn.register(ob)

    await tm1.commit()

    # 1 started before 2
    await tm1.begin()
    await tm2.begin()
    txn1 = tm1._txn
    txn2 = tm2._txn

    ob1 = await txn1.get(ob._p_oid)
    ob2 = await txn2.get(ob._p_oid)
    ob1.title = 'foobar1'
    ob2.title = 'foobar2'

    txn1.register(ob1)
    txn2.register(ob2)

    # commit 2 before 1
    await tm2.commit()
    with pytest.raises(ConflictError):
        await tm1.commit()

    await aps.remove()
    await cleanup(aps)


async def test_should_resolve_conflict_error(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm1 = TransactionManager(aps)
    tm2 = TransactionManager(aps)

    # create object first, commit it...
    await tm1.begin()
    txn = tm1._txn

    ob1 = create_ob()
    ob2 = create_ob()
    txn.register(ob1)
    txn.register(ob2)

    await tm1.commit()

    # 1 started before 2
    await tm1.begin()
    await tm2.begin()
    txn1 = tm1._txn
    txn2 = tm2._txn

    ob1 = await txn1.get(ob1._p_oid)
    ob2 = await txn2.get(ob2._p_oid)

    txn1.register(ob1)
    txn2.register(ob2)

    # commit 2 before 1
    await tm2.commit()
    # XXX should not raise conflict error
    await tm1.commit()

    await aps.remove()
    await cleanup(aps)


async def test_count_total_objects(postgres, dummy_request):
    request = dummy_request  # noqa so magically get_current_request can find

    aps = await get_aps()
    tm1 = TransactionManager(aps)

    # create object first, commit it...
    await tm1.begin()
    txn = tm1._txn

    ob = create_ob()
    txn.register(ob)

    await tm1.commit()
    await tm1.begin()
    txn1 = tm1._txn

    assert await txn1.get_total_number_of_objects() == 1
    assert await txn1.get_total_number_of_resources() == 1

    await tm1.abort()
