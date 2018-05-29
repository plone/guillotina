from guillotina.component import get_utility
from guillotina.interfaces import IAsyncJobPool
from guillotina.interfaces import IQueueUtility
from guillotina.transactions import get_transaction
from guillotina.utils import get_current_request

import uuid


class _ExecuteContext:

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def after_request(self, _name=None, _request=None):
        after_request(self.func, _name=_name, _request=_request, *self.args, **self.kwargs)

    def after_request_failed(self, _name=None, _request=None):
        after_request_failed(self.func, _name=_name, _request=_request, *self.args, **self.kwargs)

    def after_commit(self, _request=None):
        after_commit(self.func, _request=_request, *self.args, **self.kwargs)


class _GenerateQueueView:

    def __init__(self, func, request, args, kwargs):
        self.func = func
        self.request = request
        self.args = args
        self.kwargs = kwargs

    async def __call__(self):
        await self.func(*self.args, **self.kwargs)


def in_queue_with_func(func, *args, _request=None, **kwargs):
    if _request is None:
        _request = get_current_request()
    view = _GenerateQueueView(func, _request, args, kwargs)
    return in_queue(view)


def in_queue(view):
    util = get_utility(IQueueUtility)
    return _ExecuteContext(util.add, view)


async def __add_to_pool(func, request, args, kwargs):
    # make add_job async
    util = get_utility(IAsyncJobPool)
    util.add_job(func, request=request, args=args, kwargs=kwargs)


def in_pool(func, *args, request=None, **kwargs):
    return _ExecuteContext(__add_to_pool, func, request, args, kwargs)


def after_request(func, *args, _name=None, _request=None, _scope='', **kwargs):
    if _name is None:
        _name = uuid.uuid4().hex
    if _request is not None:
        request = _request
    elif 'request' in kwargs:
        request = kwargs['request']
    else:
        request = get_current_request()

    request.add_future(_name, func, scope=_scope, args=args, kwargs=kwargs)


def after_request_failed(func, *args, _name=None, _request=None, **kwargs):
    after_request(func, _name=_name, _request=_request, _scope='failed', *args, **kwargs)


def after_commit(func, *args, _request=None, **kwargs):
    if _request is not None:
        request = _request
    elif 'request' in kwargs:
        request = kwargs['request']
    else:
        request = get_current_request()

    txn = get_transaction(request)
    txn.add_after_commit_hook(func, args=args, kwargs=kwargs)


def before_commit(func, *args, _request=None, **kwargs):
    if _request is not None:
        request = _request
    elif 'request' in kwargs:
        request = kwargs['request']
    else:
        request = get_current_request()

    txn = get_transaction(request)
    txn.add_before_commit_hook(func, args=args, kwargs=kwargs)
