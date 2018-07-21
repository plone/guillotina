from aiohttp import web_request
from typing import Callable, Any, Coroutine
from collections import OrderedDict
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from guillotina.profile import profilable
from typing import Dict
from zope.interface import implementer

import asyncio
import time
import uuid


@implementer(IRequest, IDefaultLayer)
class Request(web_request.Request):
    """
    Guillotina specific request type.
    We store potentially a lot of state onto the request
    object as it is essential our poor man's thread local model
    """

#    _db_id = None
#    _tm = None
#    _txn = None
#    _container_id = None
#    container = None
#    container_settings = None
#    tail = None
#    resource = None
#    security = None

    _db_write_enabled = True
    _futures: dict = {}
    _uid = None
    _view_error = False
    _events: dict = {}

    application = None
    exc = None
    view_name = None
    found_view = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._futures: dict = {}
        self._events = OrderedDict()
        self._initialized = time.time()
        #: Dictionary of matched path parameters on request
        self.matchdict: Dict[str, str] = {}

    def record(self, event_name: str):
        '''
        Record event on the request

        :param event_name: name of event
        '''
        self._events[event_name] = time.time()

    def add_future(self, name: str, fut: Callable[..., Coroutine[Any, Any, Any]],
                   scope: str='', args=None, kwargs=None):
        '''
        Register a future to be executed after the request has finished.

        :param name: name of future
        :param fut: future to execute after request
        :param scope: group the futures to execute different groupings together
        :param args: arguments to execute future with
        :param kwargs: kwargs to execute future with
        '''
        if scope not in self._futures:
            self._futures[scope] = {}
        self._futures[scope][name] = {
            'fut': fut,
            'args': args,
            'kwargs': kwargs
        }

    def get_future(self, name: str, scope: str=''):
        '''
        Get a registered future

        :param name: scoped futures to execute. Leave default for normal behavior
        :param scope: scope name the future was registered for
        '''
        try:
            if scope not in self._futures:
                return
            return self._futures[scope][name]['fut']
        except (AttributeError, KeyError):
            return

    @property
    def events(self):
        return self._events

    @property
    def futures(self):
        return self._futures

    @property
    def view_error(self):
        return self._view_error

    @profilable
    def execute_futures(self, scope: str=''):
        '''
        Execute all the registered futures in a new task

        :param scope: scoped futures to execute. Leave default for normal behavior
        '''
        if scope not in self._futures:
            return
        futures = []
        for fut_data in self._futures[scope].values():
            fut = fut_data['fut']
            if not asyncio.iscoroutine(fut):
                fut = fut(*fut_data.get('args') or [], **fut_data.get('kwargs') or {})
            futures.append(fut)
        self._futures[scope] = {}
        if len(futures) > 0:
            task = asyncio.ensure_future(asyncio.gather(*futures))
            return task

    def clear_futures(self):
        self._futures = {}

    @property
    def uid(self):
        if self._uid is None:
            if 'X-FORWARDED-REQUEST-UID' in self.headers:
                self._uid = self.headers['X-FORWARDED-REQUEST-UID']
            else:
                self._uid = uuid.uuid4().hex
        return self._uid
