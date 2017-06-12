# -*- coding: utf-8 -*-
from aiohttp.web import Request
from aiohttp.web_exceptions import HTTPUnauthorized
from collections import MutableMapping
from guillotina.exceptions import RequestNotFound
from guillotina.interfaces import IContainer
from guillotina.interfaces import IPrincipal
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from hashlib import sha256 as sha
from zope.interface.interfaces import IInterface

import asyncio
import fnmatch
import importlib
import inspect
import logging
import random
import string
import sys
import time
import types
import typing


try:
    from aiohttp.web_server import RequestHandler
except ImportError:
    from aiohttp.web import RequestHandler  # noqa


try:
    random = random.SystemRandom()
    using_sys_random = True
except NotImplementedError:
    using_sys_random = False


RANDOM_SECRET = random.randint(0, 1000000)
logger = logging.getLogger('guillotina')


def import_class(import_string: str) -> types.ModuleType:
    """
    Import class from string
    """
    t = import_string.rsplit('.', 1)
    return getattr(importlib.import_module(t[0]), t[1], None)


def get_content_path(content: IResource) -> str:
    """
    Generate full path of resource object
    """
    parts = []
    parent = getattr(content, '__parent__', None)
    while content is not None and content.__name__ is not None and\
            parent is not None and not IContainer.providedBy(content):
        parts.append(content.__name__)
        content = parent
        parent = getattr(content, '__parent__', None)
    return '/' + '/'.join(reversed(parts))


def get_content_depth(content: IResource) -> int:
    """
    Calculate the depth of a resource object
    """
    depth = 0
    for parent in iter_parents(content):
        depth += 1
    return depth


def iter_parents(content: IResource) -> typing.Iterator[IResource]:
    """
    Iterate through all the parents of a content object
    """
    content = getattr(content, '__parent__', None)
    while content is not None:
        yield content
        content = getattr(content, '__parent__', None)


def get_authenticated_user(request: IRequest) -> IPrincipal:
    """
    Get the currently authenticated user
    """
    if (hasattr(request, 'security') and
            hasattr(request.security, 'participations') and
            len(request.security.participations) > 0):
        return request.security.participations[0].principal
    else:
        return None


def get_authenticated_user_id(request: IRequest) -> str:
    """
    Get the currently authenticated user id
    """
    user = get_authenticated_user(request)
    if user:
        return user.id


def apply_cors(request: IRequest) -> dict:
    """Second part of the cors function to validate."""
    from guillotina import app_settings
    headers = {}
    origin = request.headers.get('Origin', None)
    if origin:
        if not any([fnmatch.fnmatchcase(origin, o)
                    for o in app_settings['cors']['allow_origin']]):
            logger.error('Origin %s not allowed' % origin)
            raise HTTPUnauthorized()
        elif request.headers.get('Access-Control-Allow-Credentials', False):
            headers['Access-Control-Allow-Origin', origin]
        else:
            if any([o == "*" for o in app_settings['cors']['allow_origin']]):
                headers['Access-Control-Allow-Origin'] = '*'
            else:
                headers['Access-Control-Allow-Origin'] = origin
    if request.headers.get(
            'Access-Control-Request-Method', None) != 'OPTIONS':
        if app_settings['cors']['allow_credentials']:
            headers['Access-Control-Allow-Credentials'] = 'True'
        if len(app_settings['cors']['allow_headers']):
            headers['Access-Control-Expose-Headers'] = \
                ', '.join(app_settings['cors']['allow_headers'])
    return headers


def strings_differ(string1: str, string2: str) -> bool:
    """Check whether two strings differ while avoiding timing attacks.

    This function returns True if the given strings differ and False
    if they are equal.  It's careful not to leak information about *where*
    they differ as a result of its running time, which can be very important
    to avoid certain timing-related crypto attacks:

        http://seb.dbzteam.org/crypto/python-oauth-timing-hmac.pdf

    """
    if len(string1) != len(string2):
        return True

    invalid_bits = 0
    for a, b in zip(string1, string2):
        invalid_bits += a != b

    return invalid_bits != 0


def get_random_string(length: int=30,
                      allowed_chars: str=string.ascii_letters + string.digits) -> str:
    """
    Heavily inspired by Plone/Django
    Returns a securely generated random string.
    """
    if not using_sys_random:
        # do our best to get secure random without sysrandom
        seed_value = "%s%s%s" % (random.getstate(), time.time(), RANDOM_SECRET)
        random.seed(sha(seed_value).digest())
    return ''.join([random.choice(allowed_chars) for i in range(length)])


def resolve_dotted_name(name: str, module: str=None) -> type:
    """
    import the provided dotted name
    """
    if not isinstance(name, str):
        return name  # already an object
    name = name.split('.')
    if not name[0]:
        if module is None:
            raise ValueError("relative name without base module")
        module = module.split('.')
        name.pop(0)
        while not name[0]:
            module.pop()
            name.pop(0)
        name = module + name

    used = name.pop(0)
    found = __import__(used)
    for n in name:
        used += '.' + n
        try:
            found = getattr(found, n)
        except AttributeError:
            __import__(used)
            found = getattr(found, n)

    return found


def get_caller_module(level: int=2, sys: types.ModuleType=sys) -> types.ModuleType:
    """
    Pulled out of pyramid
    """
    module_globals = sys._getframe(level).f_globals
    module_name = module_globals.get('__name__') or '__main__'
    module = sys.modules[module_name]
    return module


def get_caller_package(level=2, get_caller_module=get_caller_module) -> types.ModuleType:
    """
    Pulled out of pyramid
    """
    # get_caller_module in arglist for tests
    module = get_caller_module(level + 1)
    f = getattr(module, '__file__', '')
    if (('__init__.py' in f) or ('__init__$py' in f)):  # empty at >>>
        # Module is a package
        return module
    # Go up one level to get package
    package_name = module.__name__.rsplit('.', 1)[0]
    return sys.modules[package_name]


def resolve_module_path(path: str) -> str:
    if type(path) is str and path[0] == '.':
        caller_mod = get_caller_module()
        caller_path = get_module_dotted_name(caller_mod)
        caller_path = '.'.join(caller_path.split('.')[:-path.count('..')])
        path = caller_path + '.' + path.split('..')[-1].strip('.')
    return path


def get_module_dotted_name(ob) -> str:
    return getattr(ob, '__module__', None) or getattr(ob, '__name__', None)


def get_dotted_name(ob) -> str:
    if inspect.isclass(ob) or IInterface.providedBy(ob) or isinstance(ob, types.FunctionType):
        name = ob.__name__
    else:
        name = ob.__class__.__name__
    return ob.__module__ + '.' + name


# get_class_dotted_name is deprecated
get_class_dotted_name = get_dotted_name


def merge_dicts(d1: dict, d2: dict) -> dict:
    """
    Update two dicts of dicts recursively,
    if either mapping has leaves that are non-dicts,
    the second's leaf overwrites the first's.
    """
    # in Python 2, use .iteritems()!
    for k, v in d1.items():
        if k in d2:
            # this next check is the only difference!
            if all(isinstance(e, MutableMapping) for e in (v, d2[k])):
                d2[k] = merge_dicts(v, d2[k])
            if isinstance(v, list):
                d2[k].extend(v)
            # we could further check types and merge as appropriate here.
    d3 = d1.copy()
    d3.update(d2)
    return d3


async def apply_coroutine(func: types.FunctionType, *args, **kwargs) -> object:
    """
    Call a function with the supplied arguments.
    If the result is a coroutine, await it.
    """
    result = func(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    return result


_valid_id_characters = string.digits + string.ascii_lowercase + '.-_@$^()+'


def valid_id(_id):
    _id = _id.lower()
    # can't start with _
    if not _id or _id[0] == '_':
        return False
    return _id == ''.join([l for l in _id if l in _valid_id_characters])


def get_current_request() -> IRequest:
    """
    Return the current request by heuristically looking it up from stack
    """
    frame = inspect.currentframe()
    while frame is not None:
        request = getattr(frame.f_locals.get('self'), 'request', None)
        if request is not None:
            return request
        elif isinstance(frame.f_locals.get('request'), Request):
            return frame.f_locals['request']
        frame = frame.f_back
    raise RequestNotFound(RequestNotFound.__doc__)


try:
    import guillotina.optimizations  # noqa
except (ImportError, AttributeError):  # pragma NO COVER PyPy / PURE_PYTHON
    pass
else:
    from guillotina.optimizations import get_current_request  # noqa
