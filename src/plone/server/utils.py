# -*- coding: utf-8 -*-
from aiohttp.web import RequestHandler
from plone.server.interfaces import IView
import asyncio
import inspect


def locked(obj):
    """Return object specfic volatile asyncio lock
    :param obj:
    """
    if not hasattr(obj, '_v_lock'):
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
        if IView.providedBy(isinstance(frame.f_locals.get('self'))):
            return frame.f_locals.get('self').request
        elif isinstance(frame.f_locals.get('self'), RequestHandler):
            return frame.f_locals['request']
        frame = frame.f_back
    raise RuntimeError('Unable to find the current request')
