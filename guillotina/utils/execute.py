from guillotina.component import get_utility
from guillotina.interfaces import IAsyncJobPool
from guillotina.interfaces import IQueueUtility
from guillotina.interfaces import IView
from guillotina.transactions import get_transaction
from guillotina.utils import get_current_request
from zope.interface import implementer

from typing import Any, Coroutine, Callable, Union
import uuid


class ExecuteContext:
    '''
    Execution context object to allow you to run the function
    in different contexts.
    '''

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def after_request(self, _name=None, _request=None):
        '''
        Execute after the request has successfully finished.

        :param _name: unique identifier to give in case you want to prevent duplicates
        :param _request: provide request object to prevent request lookup
        '''
        after_request(self.func, _name=_name, _request=_request, *self.args, **self.kwargs)

    def after_request_failed(self, _name=None, _request=None):
        '''
        Execute after the request has failed or errored.

        :param _name: unique identifier to give in case you want to prevent duplicates
        :param _request: provide request object to prevent request lookup
        '''
        after_request_failed(self.func, _name=_name, _request=_request, *self.args, **self.kwargs)

    def after_commit(self, _request=None):
        '''
        Execute after we commit to the database.

        :param _request: provide request object to prevent request lookup
        '''
        after_commit(self.func, _request=_request, *self.args, **self.kwargs)

    def before_commit(self, _request=None):
        '''
        Execute just before we commit to the database.

        :param _request: provide request object to prevent request lookup
        '''
        before_commit(self.func, _request=_request, *self.args, **self.kwargs)


@implementer(IView)
class GenerateQueueView:

    def __init__(self, func, request, args, kwargs):
        self.func = func
        self.request = request
        self.args = args
        self.kwargs = kwargs

    async def __call__(self):
        await self.func(*self.args, **self.kwargs)


def in_queue_with_func(func: Callable[..., Coroutine[Any, Any, Any]], *args,
                       _request=None, **kwargs) -> ExecuteContext:
    '''
    Execute function in the async queue.

    :param func: function to be queued
    :param _request: provide request object to prevent request lookup
    :param \\*args: arguments to call the func with
    :param \\**kwargs: keyword arguments to call the func with

    :rtype: ExecuteContext
    '''
    if _request is None:
        _request = get_current_request()
    view = GenerateQueueView(func, _request, args, kwargs)
    return in_queue(view)


def in_queue(view: Union[IView, GenerateQueueView]) -> ExecuteContext:
    '''
    Execute view-type object(context, request) in the async queue.

    :param view: view to be queued

    :rtype: ExecuteContext
    '''
    util = get_utility(IQueueUtility)
    return ExecuteContext(util.add, view)


async def __add_to_pool(func: Callable[..., Coroutine[Any, Any, Any]],
                        request, args, kwargs):
    # make add_job async
    util = get_utility(IAsyncJobPool)
    util.add_job(func, request=request, args=args, kwargs=kwargs)


def in_pool(func: Callable[..., Coroutine[Any, Any, Any]],
            *args, request=None, **kwargs) -> ExecuteContext:
    '''
    Execute function in the async pool.

    :param func: function to be queued
    :param _request: provide request object to prevent request lookup.
                     Provide if function be wrapped in database transaction.
    :param \\*args: arguments to call the func with
    :param \\**kwargs: keyword arguments to call the func with

    :rtype: ExecuteContext
    '''
    return ExecuteContext(__add_to_pool, func, request, args, kwargs)


def after_request(func: Callable[..., Coroutine[Any, Any, Any]],
                  *args, _name=None, _request=None, _scope='', **kwargs):
    '''
    Execute after the request has successfully finished.

    :param func: function to be queued
    :param _name: unique identifier to give in case you want to prevent duplicates
    :param _scope: customize scope of after commit to run for instead of default(successful request)
    :param _request: provide request object to prevent request lookup
    :param \\*args: arguments to call the func with
    :param \\**kwargs: keyword arguments to call the func with
    '''
    if _name is None:
        _name = uuid.uuid4().hex
    if _request is not None:
        request = _request
    elif 'request' in kwargs:
        request = kwargs['request']
    else:
        request = get_current_request()

    request.add_future(_name, func, scope=_scope, args=args, kwargs=kwargs)


def after_request_failed(func: Callable[..., Coroutine[Any, Any, Any]],
                         *args, _name=None, _request=None, **kwargs):
    '''
    Execute after the request has failed or errored.

    :param func: function to be queued
    :param _request: provide request object to prevent request lookup
    :param \\*args: arguments to call the func with
    :param \\**kwargs: keyword arguments to call the func with
    '''
    after_request(func, _name=_name, _request=_request, _scope='failed', *args, **kwargs)


def after_commit(func: Callable, *args, _request=None, **kwargs):
    '''
    Execute a commit to the database.

    :param func: function to be queued
    :param _request: provide request object to prevent request lookup
    :param \\*args: arguments to call the func with
    :param \\**kwargs: keyword arguments to call the func with
    '''
    if _request is not None:
        request = _request
    elif 'request' in kwargs:
        request = kwargs['request']
    else:
        request = get_current_request()

    txn = get_transaction(request)
    txn.add_after_commit_hook(func, args=args, kwargs=kwargs)


def before_commit(func: Callable[..., Coroutine[Any, Any, Any]],
                  *args, _request=None, **kwargs):
    '''
    Execute before a commit to the database.

    :param func: function to be queued
    :param _request: provide request object to prevent request lookup
    :param \\*args: arguments to call the func with
    :param \\**kwargs: keyword arguments to call the func with
    '''
    if _request is not None:
        request = _request
    elif 'request' in kwargs:
        request = kwargs['request']
    else:
        request = get_current_request()

    txn = get_transaction(request)
    txn.add_before_commit_hook(func, args=args, kwargs=kwargs)
