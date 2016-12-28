# -*- coding: utf-8 -*-
from aiohttp.web_exceptions import HTTPUnauthorized
from hashlib import sha256 as sha
from plone.server import app_settings
from zope.dottedname.resolve import resolve

import fnmatch
import importlib
import json
import logging
import random
import string
import time


try:
    random = random.SystemRandom()
    using_sys_random = True
except NotImplementedError:
    using_sys_random = False


logger = logging.getLogger('plone.server')


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


async def apply_cors(request):
    """Second part of the cors function to validate."""
    headers = {}
    origin = request.headers.get('Origin', None)
    if origin:
        if not any([fnmatch.fnmatchcase(origin, o)
                    for o in app_settings['cors']['allow_origin']]):
            logger.info('Origin %s not allowed' % origin)
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
