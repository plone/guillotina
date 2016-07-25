# -*- coding: utf-8 -*-
from aiohttp.web import RequestHandler
from plone.server.exceptions import RequestNotFound
from plone.server.interfaces import IView
from zope.component import provideUtility
from plone.server.registry import ICors
import fnmatch

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
    assert getattr(request, 'conn', None) is not None, \
        'Request has no conn'
    return request.conn.transaction_manager


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

def get_authenticated_user_id(request):
    if hasattr(request, 'security') and hasattr(request.security, 'participations') \
            and len(request.security.participations) > 0:
        return request.security.participations[0].principal.id
    else:
        return None

async def apply_cors(request):
    """Second part of the cors function to validate."""
    headers = {}
    settings = request.site_settings.forInterface(ICors)
    origin = request.headers.get('Origin', None)
    if origin:
        if not any([fnmatch.fnmatchcase(origin, o)
           for o in settings.allow_origin]):
            raise HTTPUnauthorized('Origin %s not allowed' % origin)
        elif request.headers.get('Access-Control-Allow-Credentials', False):
            headers['Access-Control-Allow-Origin', origin]
        else:
            if any([o == "*" for o in settings.allow_origin]):
                headers['Access-Control-Allow-Origin'] = '*'
            else:
                headers['Access-Control-Allow-Origin'] = origin
    if request.headers.get(
            'Access-Control-Request-Method', None) != 'OPTIONS':
        if settings.allow_credentials:
            headers['Access-Control-Allow-Credentials'] = 'True'
        if len(settings.allow_headers):
            headers['Access-Control-Expose-Headers'] = \
                ', '.join(settings.allow_headers)
    return headers
