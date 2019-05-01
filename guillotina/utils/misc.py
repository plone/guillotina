from aiohttp.web import Request
from collections import MutableMapping
from functools import partial
from guillotina import glogging
from guillotina._settings import app_settings
from guillotina.component import get_utility
from guillotina.exceptions import RequestNotFound
from guillotina.interfaces import IApplication
from guillotina.interfaces import IRequest
from guillotina.profile import profilable
from hashlib import sha256 as sha

import aiotask_context
import asyncio
import inspect
import jsonschema.validators
import random
import string
import time
import types
import typing

try:
    random = random.SystemRandom()  # type: ignore
    using_sys_random = True
except NotImplementedError:
    using_sys_random = False


RANDOM_SECRET = random.randint(0, 1000000)
logger = glogging.getLogger('guillotina')


def strings_differ(string1: str, string2: str) -> bool:
    """Check whether two strings differ while avoiding timing attacks.

    This function returns True if the given strings differ and False
    if they are equal.  It's careful not to leak information about *where*
    they differ as a result of its running time, which can be very important
    to avoid certain timing-related crypto attacks:

        http://seb.dbzteam.org/crypto/python-oauth-timing-hmac.pdf

    >>> strings_differ('one', 'one')
    False
    >>> strings_differ('one', 'two')
    True

    :param string1:
    :param string2:
    """
    if len(string1) != len(string2):
        return True

    invalid_bits = 0
    for a, b in zip(string1, string2):
        invalid_bits += a != b

    return invalid_bits != 0


def get_random_string(length: int = 30,
                      allowed_chars: str = string.ascii_letters + string.digits) -> str:
    """
    Heavily inspired by Plone/Django
    Returns a securely generated random string.

    >>> get_random_string(length=10)

    :param length:
    :param allowed_chars:
    """
    if not using_sys_random:
        # do our best to get secure random without sysrandom
        seed_value = "%s%s%s" % (random.getstate(), time.time(), RANDOM_SECRET)
        random.seed(sha(seed_value.encode('utf-8')).digest())
    return ''.join([random.choice(allowed_chars) for i in range(length)])


def merge_dicts(d1: dict, d2: dict) -> dict:
    """
    Update two dicts of dicts recursively,
    if either mapping has leaves that are non-dicts,
    the second's leaf overwrites the first's.
    """
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

    >>> async def foobar(): return 'hi'
    >>> async def async_foobar(): return 'hi'
    >>> await apply_coroutine(foobar)
    'hi'
    >>> await apply_coroutine(async_foobar)
    'hi'

    :param func: function to run as coroutiune if one
    :param \\*args: args to call function with
    :param \\**kwargs: kwargs to call function with
    """
    result = func(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    return result


def loop_apply_coroutine(loop, func: types.FunctionType, *args, **kwargs) -> object:
    """
    Call a function with the supplied arguments.
    If the result is a coroutine, use the supplied loop to run it.
    """
    if asyncio.iscoroutinefunction(func):
        future = asyncio.ensure_future(
            func(*args, **kwargs), loop=loop)

        loop.run_until_complete(future)
        return future.result()
    else:
        return func(*args, **kwargs)


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
                args.append(call_kwargs.pop(param.name))
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


def to_str(value):
    if isinstance(value, bytes):
        value = value.decode('utf-8')
    return value


def deprecated(message):
    def deprecated_decorator(func):
        def deprecated_func(*args, **kwargs):
            if getattr(func, '__warned__', None) is None:
                logger.warning(
                    "{}: {}".format(func.__name__, message))
                func.__warned__ = True
            return func(*args, **kwargs)
        return deprecated_func
    return deprecated_decorator


def list_or_dict_items(val):
    if isinstance(val, list):
        new_val = []
        for item in val:
            new_val.extend([(k, v) for k, v in item.items()])
        return new_val
    return [(k, v) for k, v in val.items()]


async def run_async(func, *args, **kwargs) -> object:
    '''
    Run a non-async function in an executor

    >>> async def foobar(): return 'hi'
    >>> await run_async(foobar)
    'hi'

    :param func: function to run as coroutiune if one
    :param *args: args to call function with
    :param **kwargs: kwargs to call function with
    '''
    root = get_utility(IApplication, name='root')
    loop = asyncio.get_event_loop()
    func = partial(func, *args, **kwargs)
    return await loop.run_in_executor(root.executor, func)


def safe_unidecode(val: bytes) -> str:
    '''
    Convert bytes to a string in a safe way

    >>> safe_unidecode(b'foobar')
    'foobar'

    :param val: bytes to convert
    '''
    if isinstance(val, str):
        # already decoded
        return val

    for codec in ('utf-8', 'windows-1252', 'latin-1'):
        try:
            return val.decode(codec)
        except UnicodeDecodeError:
            pass
    return val.decode('utf-8', errors='replace')


def get_url(req, path):
    '''
    Return calculated url from a request object taking
    into account X-VirtualHost-Monster header
    '''
    if 'X-VirtualHost-Monster' in req.headers:
        virtualhost = req.headers['X-VirtualHost-Monster']
    else:
        virtualhost = None

    if virtualhost:
        return '{}/{}'.format(virtualhost.rstrip('/'), path.strip('/'))
    else:
        url = req.url.with_path(path)
        for hdr in ('X-Forwarded-Proto', 'X-Forwarded-Scheme',):
            forwarded_proto = req.headers.get(hdr, None)
            if forwarded_proto:
                url = url.with_scheme(forwarded_proto)
                break
        return str(url)


_cached_jsonschema_validators: typing.Dict[str, typing.Any] = {}


def get_schema_validator(schema_name: str):
    '''
    Get a json schema validator by the definition name

    :param schema_name: Name of the json schema type
    '''
    if schema_name in _cached_jsonschema_validators:
        return _cached_jsonschema_validators[schema_name]

    schema = {
        **app_settings['json_schema_definitions'][schema_name],
        'definitions': app_settings['json_schema_definitions']
    }
    jsonschema_validator = jsonschema.validators.validator_for(schema)
    jsonschema_validator.check_schema(schema)
    val = jsonschema_validator(schema)
    _cached_jsonschema_validators[schema_name] = val
    return val
