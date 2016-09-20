# -*- coding: utf-8 -*-
from aiohttp.test_utils import make_mocked_request
from persistent.mapping import PersistentMapping
from plone.server.browser import View
from plone.server.transactions import CallbackTransactionDataManager
from plone.server.transactions import RequestAwareDB
from plone.server.transactions import RequestAwareTransactionManager
from plone.server.transactions import TransactionProxy
import pytest
import ZODB.DemoStorage


class SetItemView(View):
    def __call__(self, name='foo', value='bar'):
        self.context[name] = value


@pytest.yield_fixture(scope='function')
def conn():
    storage = ZODB.DemoStorage.DemoStorage()
    ZODB.DB(storage).close()  # init storage with root
    db = RequestAwareDB(storage)
    tm = RequestAwareTransactionManager()
    yield db.open(transaction_manager=tm)


# noinspection PyShadowingNames
@pytest.yield_fixture(scope='function')
def root(conn):
    yield conn.root()


# noinspection PyShadowingNames,PyProtectedMember
@pytest.yield_fixture(scope='function')
def foo(root):
    request = make_mocked_request('POST', '/')
    txn = root._p_jar.transaction_manager.begin(request)
    SetItemView(root, request)('foo', PersistentMapping())
    txn.commit()
    yield root['foo']


# noinspection PyShadowingNames,PyProtectedMember
@pytest.yield_fixture(scope='function')
def bar(root):
    request = make_mocked_request('POST', '/')
    txn = root._p_jar.transaction_manager.begin(request)
    SetItemView(root, request)('bar', PersistentMapping())
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
    SetItemView(foo, request1)('a', PersistentMapping())
    # Test that object is registered
    assert hasattr(request1, '_txn')
    assert hasattr(request1, '_txn_time')
    assert hasattr(request1, '_txn_dm')
    assert foo in request1._txn_dm._registered_objects

    # Create /bar/b
    request2 = TransactionProxy(request1)
    t2 = tm.begin(request2)
    SetItemView(bar, request2)('b', PersistentMapping())
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
    SetItemView(bar, request2)('c', PersistentMapping())

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
def test_concurrent_transaction_abort_has_no_side_effects(root, foo, bar):
    tm = root._p_jar.transaction_manager

    # Create /foo/a
    request1 = make_mocked_request('POST', '/foo')
    t1 = tm.begin(request1)
    SetItemView(foo, request1)('a', PersistentMapping())

    # Test that object is registered
    assert foo in request1._txn_dm._registered_objects

    # Create /bar/b
    request2 = make_mocked_request('POST', '/bar')
    t2 = tm.begin(request2)
    SetItemView(bar, request2)('b', PersistentMapping())

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
