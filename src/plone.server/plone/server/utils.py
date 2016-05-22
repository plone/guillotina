# -*- coding: utf-8 -*-
from aiohttp.web import RequestHandler
from plone.server.exceptions import RequestNotFound
from plone.server.interfaces import IView

import asyncio
import importlib
import inspect


def locked(obj):
    """Return object specfic volatile asyncio lock
    :param obj:
    """
    try:
        assert obj._v_lock is not None
    except (AssertionError, AttributeError):
        obj._v_lock = asyncio.Lock()
    return obj._v_lock


def tm(request):
    """Return shared transaction manager (from request)
    :param request:
    """
    assert getattr(request, 'app', None) is not None, \
        'Request has no app'
    assert getattr(request.app, '_p_jar', None) is not None, \
        'App has no ZODB connection'
    return request.app._p_jar.transaction_manager


def sync(request):
    """Return shared asyncio executor instance (from request)
    :param request:
    """
    assert getattr(request, 'app', None) is not None, \
        'Request has no app'
    assert getattr(request.app, 'executor', None) is not None, \
        'App has no executor'
    return lambda *args, **kwargs: request.app.loop.run_in_executor(
        request.app.executor, *args, **kwargs)


def get_current_request():
    """Return the nearest request from the current frame"""
    frame = inspect.currentframe()
    while frame is not None:
        if IView.providedBy(frame.f_locals.get('self')):
            return frame.f_locals.get('self').request
        elif isinstance(frame.f_locals.get('self'), RequestHandler):
            return frame.f_locals['request']
        frame = frame.f_back
    raise RequestNotFound('Unable to find the current request')


def import_class(import_string):
    t = import_string.rsplit('.', 1)
    return getattr(importlib.import_module(t[0]), t[1], None)


def get_content_path(content):
    parts = []
    while content:
        parts.append(content.__name__)
        content = getattr(content, '__parent__', None)
    return '/' + '/'.join(reversed(parts))
