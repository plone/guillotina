# -*- coding: utf-8 -*-
from aiohttp.test_utils import make_mocked_request
from BTrees import OOBTree
from plone.server.browser import View
from plone.server.transactions import CallbackTransactionDataManager
from plone.server.transactions import RequestAwareDB
from plone.server.transactions import RequestAwareTransactionManager
from plone.server.transactions import TransactionProxy
from ZODB.POSException import ConflictError
from ZODB.POSException import ReadConflictError
from ZODB.tests.test_storage import MinimalMemoryStorage

import pytest
import ZODB


class SetItemView(View):
    def __call__(self, name='foo', value='bar'):
        self.context[name] = value


class RegisterView(View):
    def __call__(self):
        # noinspection PyProtectedMember
        self.context._p_changed = True


class CommitView(View):
    def __call__(self):
        # noinspection PyProtectedMember
        self.request._txn.commit()


@pytest.yield_fixture(scope='function')
def storage():
    storage = MinimalMemoryStorage()
    ZODB.DB(storage).close()  # init storage with root
    yield storage


@pytest.yield_fixture(scope='function')
def db(storage):
    yield RequestAwareDB(storage)


@pytest.yield_fixture(scope='function')
def conn1(db):
    tm = RequestAwareTransactionManager()
    yield db.open(transaction_manager=tm)


@pytest.yield_fixture(scope='function')
def conn2(db):
    tm = RequestAwareTransactionManager()
    yield db.open(transaction_manager=tm)


# noinspection PyShadowingNames
@pytest.yield_fixture(scope='function')
def root(conn1):
    yield conn1.root()


# noinspection PyShadowingNames,PyProtectedMember
@pytest.yield_fixture(scope='function')
def foo(root):
    request = make_mocked_request('POST', '/')
    txn = root._p_jar.transaction_manager.begin(request)
    SetItemView(root, request)('foo', OOBTree.OOBTree())
    txn.commit()
    yield root['foo']


# noinspection PyShadowingNames,PyProtectedMember
@pytest.yield_fixture(scope='function')
def bar(root):
    request = make_mocked_request('POST', '/')
    txn = root._p_jar.transaction_manager.begin(request)
    SetItemView(root, request)('bar', OOBTree.OOBTree())
    txn.commit()
    yield root['bar']


# noinspection PyShadowingNames,PyProtectedMember
def test_root_fixture(root):
    assert root is root._p_jar.root()


# noinspection PyShadowingNames,PyProtectedMember
def test_root_foo_fixture(root, foo):
    assert foo is root['foo']
    assert root._p_serial is not foo._p_serial


# noinspection PyShadowingNames,PyProtectedMember
def test_root_bar_fixture(root, bar):
    assert bar is root['bar']
    assert root._p_serial is not bar._p_serial


# noinspection PyShadowingNames,PyProtectedMember
def test_foo_bar_fixture(foo, bar):
    assert foo is not bar
    assert foo._p_serial is not bar._p_serial


# noinspection PyShadowingNames,PyProtectedMember
def test_transaction_proxy(root, foo, bar):
    tm = root._p_jar.transaction_manager

    # Create /foo/a
    request1 = make_mocked_request('POST', '/foo')
    t1 = tm.begin(request1)
    SetItemView(foo, request1)('a', OOBTree.OOBTree())
    # Test that object is registered
    assert hasattr(request1, '_txn')
    assert hasattr(request1, '_txn_time')
    assert hasattr(request1, '_txn_dm')
    assert foo in request1._txn_dm._registered_objects

    # Create /bar/b
    request2 = TransactionProxy(request1)
    t2 = tm.begin(request2)
    SetItemView(bar, request2)('b', OOBTree.OOBTree())
    # Test that object is registered
    assert hasattr(request2, '_txn')
    assert hasattr(request2, '_txn_time')
    assert hasattr(request2, '_txn_dm')
    assert bar in request2._txn_dm._registered_objects

    # Test that two transactions are indepedent
    assert t1 is not t2
    assert t1 is request1._txn
    assert t2 is request2._txn
    assert request1._txn_time < request2._txn_time
    assert bar not in request1._txn_dm._registered_objects
    assert foo not in request2._txn_dm._registered_objects
    assert len(request1._txn_dm._registered_objects) == 1
    assert len(request2._txn_dm._registered_objects) == 1

    # Create /bar/c
    SetItemView(bar, request2)('c', OOBTree.OOBTree())

    # Test that registered objects are not affected
    assert len(request1._txn_dm._registered_objects) == 1
    assert len(request2._txn_dm._registered_objects) == 1

    # Commit
    t1.commit()
    t2.commit()

    # Test that /foo/a and /bar/b have different transaction
    assert foo['a']._p_serial != bar['b']._p_serial

    # Test that /bar/b and /bar/c have the same transaction
    assert bar['b']._p_serial == bar['c']._p_serial


# noinspection PyShadowingNames,PyProtectedMember
def test_callback_transaction_data_manager_with_commit(root):
    tm = root._p_jar.transaction_manager
    request = make_mocked_request('POST', '/')
    view = View(root, request)

    # Test that callback is called after commit
    txn = tm.get(request)
    txn.join(CallbackTransactionDataManager(setattr, view, 'value', True))
    assert getattr(view, 'value', None) is None
    txn.commit()
    assert getattr(view, 'value', None) is True


# noinspection PyShadowingNames,PyProtectedMember
def test_callback_transaction_data_manager_with_abort(root):
    tm = root._p_jar.transaction_manager
    request = make_mocked_request('POST', '/')
    view = View(root, request)

    # Test that callback is not called after abort
    txn = tm.get(request)
    txn.join(CallbackTransactionDataManager(setattr, view, 'value', True))
    assert getattr(view, 'value', None) is None
    txn.abort()
    assert getattr(view, 'value', None) is None


# noinspection PyShadowingNames,PyProtectedMember
def test_concurrent_transaction_abort_has_no_side_effects(root, foo, bar):  # noqa
    tm = root._p_jar.transaction_manager

    # Create /foo/a
    request1 = make_mocked_request('POST', '/foo')
    t1 = tm.begin(request1)
    SetItemView(foo, request1)('a', OOBTree.OOBTree())

    # Test that object is registered
    assert foo in request1._txn_dm._registered_objects

    # Create /bar/b
    request2 = make_mocked_request('POST', '/bar')
    t2 = tm.begin(request2)
    SetItemView(bar, request2)('b', OOBTree.OOBTree())

    # Test that object is registered
    assert bar in request2._txn_dm._registered_objects

    # Test that two transactions are indepedent
    assert bar not in request1._txn_dm._registered_objects
    assert foo not in request2._txn_dm._registered_objects

    # Abort the first transaction
    t1.abort()

    # Commit the second transaction
    t2.commit()

    # Test that /foo/a has not been created by t1
    assert 'a' not in foo

    # Test that /bar/b has been created by t2
    assert 'b' in bar


# noinspection PyShadowingNames,PyProtectedMember
def test_multiple_connections(conn1, conn2):  # noqa
    root1 = conn1.root()
    root2 = conn2.root()

    request = make_mocked_request('POST', '/')
    txn = root1._p_jar.transaction_manager.begin(request)
    SetItemView(root1, request)('foo', OOBTree.OOBTree())
    txn.commit()

    assert 'foo' in root1
    assert 'foo' not in root2

    conn2.newTransaction(None)

    assert 'foo' in root2

    request1 = make_mocked_request('POST', '/')
    txn1 = root1._p_jar.transaction_manager.begin(request1)
    SetItemView(root1['foo'], request1)('bar', True)

    request2 = make_mocked_request('POST', '/')
    txn2 = root2._p_jar.transaction_manager.begin(request2)
    SetItemView(root2['foo'], request2)('bar', False)

    txn1.commit()

    assert root1['foo']['bar']
    assert not root2['foo']['bar']

    with pytest.raises(ConflictError):
        txn2.commit()

    assert root2['foo']['bar']


# noinspection PyShadowingNames,PyProtectedMember
def test_request_aware_read_current(foo):  # noqa
    request1 = make_mocked_request('POST', '/')
    foo._p_jar.transaction_manager.begin(request1)

    request2 = make_mocked_request('POST', '/')
    foo._p_jar.transaction_manager.begin(request2)

    for i in range(0, 5):
        SetItemView(foo, request1)(str(i), OOBTree.OOBTree())

    assert '_txn_readCurrent' in request1.__dict__
    assert len(request1._txn_readCurrent) > 0

    CommitView(foo, request1)()

    assert len(request1._txn_readCurrent) == 0

    for i in range(5, 10):
        SetItemView(foo, request2)(str(i), OOBTree.OOBTree())

    assert '_txn_readCurrent' in request2.__dict__
    assert len(request2._txn_readCurrent) > 0

    CommitView(foo, request2)()

    assert len(request2._txn_readCurrent) == 0


# noinspection PyShadowingNames,PyProtectedMember
def test_concurrent_btree_write(foo, conn2):  # noqa
    bar = conn2.root()['foo']

    # Init a few buckets
    request = make_mocked_request('POST', '/')
    foo._p_jar.transaction_manager.begin(request)
    for i in range(0, 50):
        SetItemView(foo, request)(str(i), OOBTree.OOBTree())
    CommitView(foo, request)()

    assert '1' in foo
    assert '1' not in bar

    bar._p_jar.newTransaction(None)
    assert '1' in bar

    # Concurrent requests on different connections
    request1 = make_mocked_request('POST', '/')
    foo._p_jar.transaction_manager.begin(request1)

    request2 = make_mocked_request('POST', '/')
    bar._p_jar.transaction_manager.begin(request2)

    # Mutate one bucket
    for i in range(100, 101):
        SetItemView(foo, request1)(str(i), OOBTree.OOBTree())

    assert '_txn_readCurrent' in request1.__dict__
    assert len(request1._txn_readCurrent) > 0

    CommitView(foo, request1)()

    assert len(request1._txn_readCurrent) == 0

    # Mutate another bucket on another connection without sync
    for i in range(500, 501):
        SetItemView(bar, request2)(str(i), OOBTree.OOBTree())

    assert '_txn_readCurrent' in request2.__dict__
    assert len(request2._txn_readCurrent) > 0

    CommitView(bar, request2)()

    assert len(request2._txn_readCurrent) == 0


# noinspection PyShadowingNames,PyProtectedMember
def test_concurrent_read_current_conflict(foo, conn2):  # noqa
    bar = conn2.root()['foo']

    # Init a few buckets
    request = make_mocked_request('POST', '/')
    foo._p_jar.transaction_manager.begin(request)
    for i in range(0, 50):
        SetItemView(foo, request)(str(i), OOBTree.OOBTree())
    CommitView(foo, request)()

    bar._p_jar.newTransaction(None)

    # Concurrent requests on different connections
    request1 = make_mocked_request('POST', '/')
    foo._p_jar.transaction_manager.begin(request1)

    request2 = make_mocked_request('POST', '/')
    bar._p_jar.transaction_manager.begin(request2)

    # Mutate one bucket
    for i in range(100, 101):
        SetItemView(foo, request1)(str(i), OOBTree.OOBTree())

    # Force BTree mutation only on the first connection
    RegisterView(foo, request1)()
    CommitView(foo, request1)()

    # Mutate another bucket on another connection without sync
    for i in range(500, 501):
        SetItemView(bar, request2)(str(i), OOBTree.OOBTree())

    # ReadConflictError should be raised, because 'bar' has
    # been marked as current

    assert bar._p_oid in request2._txn_readCurrent.keys()
    assert request2._txn_readCurrent[bar._p_oid] == bar._p_serial

    with pytest.raises(ReadConflictError):
        CommitView(bar, request2)()
