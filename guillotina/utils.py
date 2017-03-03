# -*- coding: utf-8 -*-
from aiohttp.web_exceptions import HTTPUnauthorized
from collections import MutableMapping
from hashlib import sha256 as sha
from zope.dottedname.resolve import resolve

import fnmatch
import importlib
import logging
import random
import string
import sys
import time


try:
    random = random.SystemRandom()
    using_sys_random = True
except NotImplementedError:
    using_sys_random = False


logger = logging.getLogger('guillotina')


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


def get_content_depth(content):
    depth = 0
    for parent in iter_parents(content):
        depth += 1
    return depth


def iter_parents(content):
    content = getattr(content, '__parent__', None)
    while content:
        yield content
        content = getattr(content, '__parent__', None)


def get_authenticated_user(request):
    if (hasattr(request, 'security') and
            hasattr(request.security, 'participations') and
            len(request.security.participations) > 0):
        return request.security.participations[0].principal
    else:
        return None


def get_authenticated_user_id(request):
    user = get_authenticated_user(request)
    if user:
        return user.id


def apply_cors(request):
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


def strings_differ(string1, string2):
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


class Lazy(object):
    """Lazy Attributes."""

    def __init__(self, func, name=None):
        if name is None:
            name = func.__name__
        self.data = (func, name)

    def __get__(self, inst, class_):
        if inst is None:
            return self

        func, name = self.data
        value = func(inst)
        inst.__dict__[name] = value

        return value


def resolve_or_get(potential_dotted_name):
    if isinstance(potential_dotted_name, str):
        return resolve(potential_dotted_name)
    return potential_dotted_name


RANDOM_SECRET = random.randint(0, 1000000)


def get_random_string(length=30, allowed_chars=string.ascii_letters + string.digits):
    """
    Heavily inspired by Plone/Django
    Returns a securely generated random string.
    """
    if not using_sys_random:
        # do our best to get secure random without sysrandom
        seed_value = "%s%s%s" % (random.getstate(), time.time(), RANDOM_SECRET)
        random.seed(sha(seed_value).digest())
    return ''.join([random.choice(allowed_chars) for i in range(length)])


def caller_module(level=2, sys=sys):
    """
    Pulled out of pyramid
    """
    module_globals = sys._getframe(level).f_globals
    module_name = module_globals.get('__name__') or '__main__'
    module = sys.modules[module_name]
    return module


def caller_package(level=2, caller_module=caller_module):
    """
    Pulled out of pyramid
    """
    # caller_module in arglist for tests
    module = caller_module(level + 1)
    f = getattr(module, '__file__', '')
    if (('__init__.py' in f) or ('__init__$py' in f)):  # empty at >>>
        # Module is a package
        return module
    # Go up one level to get package
    package_name = module.__name__.rsplit('.', 1)[0]
    return sys.modules[package_name]


def resolve_module_path(path):
    if type(path) is str and path[0] == '.':
        caller_mod = caller_module()
        caller_path = dotted_name(caller_mod)
        caller_path = '.'.join(caller_path.split('.')[:-path.count('..')])
        path = caller_path + '.' + path.split('..')[-1].strip('.')
    return path


def dotted_name(ob):
    return getattr(ob, '__module__', None) or getattr(ob, '__name__', '')


def rec_merge(d1, d2):
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
                d2[k] = rec_merge(v, d2[k])
            if isinstance(v, list):
                d2[k].extend(v)
            # we could further check types and merge as appropriate here.
    d3 = d1.copy()
    d3.update(d2)
    return d3
