from aiohttp.web import Request
from collections import MutableMapping
from guillotina import glogging
from guillotina.component import get_utility
from guillotina.exceptions import RequestNotFound
from guillotina.interfaces import IApplication
from guillotina.interfaces import IContainer
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPrincipal
from guillotina.interfaces import IPrincipalRoleMap
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.profile import profilable
from hashlib import sha256 as sha
from zope.interface.interfaces import IInterface

import aiotask_context
import asyncio
import importlib
import inspect
import os
import pathlib
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
logger = glogging.getLogger('guillotina')


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


def resolve_dotted_name(name: str) -> type:
    """
    import the provided dotted name
    """
    if not isinstance(name, str):
        return name  # already an object
    name = name.split('.')
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
    if not _id or _id[0] in ('_', '@'):
        return False
    return _id == ''.join([l for l in _id if l in _valid_id_characters])


async def get_containers(request, transaction_strategy='none'):
    root = get_utility(IApplication, name='root')
    for _id, db in root:
        if IDatabase.providedBy(db):
            tm = request._tm = db.get_transaction_manager()
            tm.request = request
            request._db_id = _id
            request._txn = txn = await tm.begin(request)
            items = {(k, v) async for k, v in db.async_items()}
            await tm.abort(txn=txn)

            for s_id, container in items:
                request._txn = txn = await tm.begin(request)
                tm.request.container = container
                tm.request._container_id = container.id
                if hasattr(request, 'container_settings'):
                    del request.container_settings
                yield txn, tm, container
                try:
                    # do not rely on consumer of object to always close it.
                    # there is no harm in aborting twice
                    await tm.abort(txn=txn)
                except Exception:
                    logger.warn('Error aborting transaction', exc_info=True)


@profilable
def get_current_request() -> IRequest:
    """
    Return the current request by heuristically looking it up from stack
    """
    try:
        task_context = aiotask_context.get('request')
        if task_context is not None:
            return task_context
    except (ValueError, AttributeError, RuntimeError):
        pass

    # fallback
    frame = inspect.currentframe()
    while frame is not None:
        request = getattr(frame.f_locals.get('self'), 'request', None)
        if request is not None:
            return request
        elif isinstance(frame.f_locals.get('request'), Request):
            return frame.f_locals['request']
        frame = frame.f_back
    raise RequestNotFound(RequestNotFound.__doc__)


def get_owners(obj):
    try:
        prinrole = IPrincipalRoleMap(obj)
    except TypeError:
        return []
    owners = []
    for user, roles in prinrole._bycol.items():
        for role in roles:
            if role == 'guillotina.Owner':
                owners.append(user)
    if len(owners) == 0 and getattr(obj, '__parent__', None) is not None:
        # owner can be parent if none found on current object
        return get_owners(obj.__parent__)
    return owners


def resolve_path(file_path):
    if ':' in file_path:
        # referencing a module
        dotted_mod_name, _, rel_path = file_path.partition(':')
        module = resolve_dotted_name(dotted_mod_name)
        if module is None:
            raise Exception('Invalid module for static directory {}'.format(file_path))
        file_path = os.path.join(
            os.path.dirname(os.path.realpath(module.__file__)), rel_path)
    return pathlib.Path(file_path)


def lazy_apply(func, *call_args, **call_kwargs):
    '''
    apply arguments in the order that they come in the function signature
    and do not apply if argument not provided

    call_args will be applied in order if func signature has args.
    otherwise, call_kwargs is the magic here...
    '''
    sig = inspect.signature(func)
    args = []
    kwargs = {}
    for idx, param_name in enumerate(sig.parameters):
        param = sig.parameters[param_name]
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            if param.name in call_kwargs:
                kwargs.append(call_kwargs.pop(param.name))
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            kwargs.update(call_kwargs)  # this will be the last iteration...
            continue

        if param.kind == inspect.Parameter.POSITIONAL_ONLY:
            if len(call_args) >= (idx + 1):
                args.append(call_args[idx])
            elif param.name in call_kwargs:
                args.append(call_kwargs.pop(param.name))
        else:
            if param.name in call_kwargs:
                kwargs[param.name] = call_kwargs.pop(param.name)
            elif (param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD and
                    len(call_args) >= (idx + 1)):
                args.append(call_args[idx])
    return func(*args, **kwargs)


async def navigate_to(obj, path):
    actual = obj
    path_components = path.strip('/').split('/')
    for p in path_components:
        if p != '':
            item = await actual.async_get(p)
            if item is None:
                raise KeyError('No %s in %s' % (p, actual))
            else:
                actual = item
    return actual


def to_str(value):
    if isinstance(value, bytes):
        value = value.decode('utf-8')
    return value
