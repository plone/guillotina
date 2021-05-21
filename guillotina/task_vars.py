from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionManager
from guillotina.interfaces import IContainer
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPrincipal
from guillotina.interfaces import IRegistry
from guillotina.interfaces import IRequest
from guillotina.interfaces import ISecurityPolicy
from typing import Dict
from typing import Generic
from typing import Optional
from typing import TypeVar

import asyncio
import contextvars
import weakref


# This global dictionary keeps all the contextvars for each task.
# When a task finishes and is destroyed, the context is destroyed as well
_context = weakref.WeakKeyDictionary()  # type: ignore


class FakeTask:
    """
    This class is necessary because we need an object to use as a key in the WeakKeyDictionary _context.
    We can't use built-in objects because they don't have the `__weakref__` in the `__slots__` and without
    this attribute, weakreaf.ref doesn't work
    """


_no_task_fallback = FakeTask()


def copy_context(coro):
    """
    This function it's similar contextvars.copy_context() but has a slightly different
    signature and it's not called by default when a new task/future is created.

    To copy the context from the current task to a new one you need to call this
    funcion explicitly, like this:

        async def worker():
            pass
            # ...

        asyncio.create_task(copy_context(worker()))

    """
    try:
        from_task = asyncio.current_task()
    except RuntimeError:
        assert _no_task_fallback is not None
        from_task = _no_task_fallback

    async def _wrapper():
        nonlocal from_task
        task = asyncio.current_task()
        assert task != from_task
        # The _context value type is a dict so we need to copy the dict to avoid
        # sharing the same context in different tasks
        _context[task] = _context[from_task].copy()
        del from_task
        return await coro

    return _wrapper()


_T = TypeVar("_T")
_NO_DEFAULT = object()


class Token:
    """
    Reimplementation of contextvars.Token
    """

    MISSING = contextvars.Token.MISSING

    def __init__(self, var, old_value) -> None:
        self._var = var
        self._old_value = old_value

    @property
    def var(self):
        return self._var

    @property
    def old_value(self):
        return self._old_value


class ShyContextVar(Generic[_T]):
    """
    Reimplementation of contextvars.ContextVar but stores the values to the global `_context`
    instead of storing it to the PyContext
    """

    def __init__(self, name: str, default=_NO_DEFAULT):
        self._name = name
        self._default = default

    @property
    def name(self):
        return self._name

    def get(self, default=_NO_DEFAULT):
        ctx = self._get_ctx_data()
        if self._name in ctx:
            return ctx[self._name]
        elif default != _NO_DEFAULT:
            return default
        elif self._default != _NO_DEFAULT:
            return self._default
        else:
            raise LookupError(self)

    def set(self, value) -> Token:
        data = self._get_ctx_data()
        name = self._name
        if name in data:
            t = Token(self, data[name])
        else:
            t = Token(self, Token.MISSING)
        data[self._name] = value
        return t

    def reset(self, token):
        if token.old_value == Token.MISSING:
            ctx = self._get_ctx_data()
            if ctx and self._name in ctx:
                del ctx[self._name]
        else:
            self.set(token.old_value)

    def _get_ctx_data(self):
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = _no_task_fallback
        try:
            data = _context[task]
        except KeyError:
            data = {}
            _context[task] = data
        return data


request: ShyContextVar[Optional[IRequest]] = ShyContextVar("g_request", default=None)
txn: ShyContextVar[Optional[ITransaction]] = ShyContextVar("g_txn", default=None)
tm: ShyContextVar[Optional[ITransactionManager]] = ShyContextVar("g_tm", default=None)
futures: ShyContextVar[Optional[Dict]] = ShyContextVar("g_futures", default=None)
authenticated_user: ShyContextVar[Optional[IPrincipal]] = ShyContextVar("g_authenticated_user", default=None)
security_policies: ShyContextVar[Optional[Dict[str, ISecurityPolicy]]] = ShyContextVar(
    "g_security_policy", default=None
)
container: ShyContextVar[Optional[IContainer]] = ShyContextVar("g_container", default=None)
registry: ShyContextVar[Optional[IRegistry]] = ShyContextVar("g_registry", default=None)
db: ShyContextVar[Optional[IDatabase]] = ShyContextVar("g_database", default=None)
