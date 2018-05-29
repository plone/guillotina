from guillotina.utils import get_current_request
import uuid
from guillotina.transactions import get_transaction


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


def after_commit(func, *args, _name=None, _request=None, **kwargs):
    if _request is not None:
        request = _request
    elif 'request' in kwargs:
        request = kwargs['request']
    else:
        request = get_current_request()

    txn = get_transaction(request)
    txn.add_after_commit_hook(func, args=args, kwargs=kwargs)
