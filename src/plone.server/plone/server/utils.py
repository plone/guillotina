# -*- coding: utf-8 -*-
from aiohttp.web_exceptions import HTTPUnauthorized
from plone.server.registry import ICors

import fnmatch
import importlib


def import_class(import_string):
    t = import_string.rsplit('.', 1)
    return getattr(importlib.import_module(t[0]), t[1], None)


def get_content_path(content):
    """ No site id
    """
    parts = []
    parent = getattr(content, '__parent__', None)
    while content is not None and content.__name__ is not None and\
            parent is not None:
        parts.append(content.__name__)
        content = parent
        parent = getattr(content, '__parent__', None)
    return '/' + '/'.join(reversed(parts))


def iter_parents(content):
    content = getattr(content, '__parent__', None)
    while content:
        yield content
        content = getattr(content, '__parent__', None)


def get_authenticated_user_id(request):
    if hasattr(request, 'security') and hasattr(request.security, 'participations') \
            and len(request.security.participations) > 0:
        return request.security.participations[0].principal.id
    else:
        return None


class DefaultRootCors(object):
    enabled = True
    allow_origin = ['*']
    allow_methods = ['GET', 'POST', 'OPTIONS']
    allow_headers = ['*']
    expose_headers = []
    allow_credentials = True
    max_age = 3660

async def apply_cors(request):
    """Second part of the cors function to validate."""
    headers = {}
    if not hasattr(request, 'site_settings'):
        settings = DefaultRootCors()
    else:
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
