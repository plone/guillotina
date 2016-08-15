# -*- coding: utf-8 -*-
from aiohttp.test_utils import make_mocked_request
from plone.server.browser import View
from plone.server.transactions import CallbackTransactionDataManager
from plone.server.transactions import RequestAwareDB
from plone.server.transactions import RequestAwareTransactionManager
from plone.server.transactions import TransactionProxy
import pytest
import ZODB.DemoStorage


@pytest.yield_fixture(scope='function')
def conn():
    storage = ZODB.DemoStorage.DemoStorage()
    ZODB.DB(storage).close()  # init storage with root
    db = RequestAwareDB(storage)
    tm = RequestAwareTransactionManager()
    yield db.open(transaction_manager=tm)


@pytest.yield_fixture(scope='function')
def view(conn):
    request = make_mocked_request('POST', '/')
    yield View(conn.root(), request)


def test_transaction_proxy(view):
    tm = view.context._p_jar.transaction_manager

    request1 = view.request
    t1 = tm.begin(request1)
    assert hasattr(request1, '_txn')
    assert hasattr(request1, '_txn_time')

    request2 = TransactionProxy(view.request)
    t2 = tm.begin(request2)
    assert hasattr(request2, '_txn')
    assert hasattr(request2, '_txn_time')

    assert t1 is not t2
    assert t1 is request1._txn
    assert t2 is request2._txn
    assert request1._txn_time < request2._txn_time


def test_callback_transaction_data_manager_with_commit(view):
    tm = view.context._p_jar.transaction_manager
    txn = tm.get(view.request)
    txn.join(CallbackTransactionDataManager(setattr, view, 'value', True))
    assert getattr(view, 'value', None) is None
    txn.commit()
    assert getattr(view, 'value', None) is True


def test_callback_transaction_data_manager_with_abort(view):
    tm = view.context._p_jar.transaction_manager
    txn = tm.get(view.request)
    txn.join(CallbackTransactionDataManager(setattr, view, 'value', True))
    assert getattr(view, 'value', None) is None
    txn.abort()
    assert getattr(view, 'value', None) is None
