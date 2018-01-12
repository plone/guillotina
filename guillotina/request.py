from aiohttp import web_request
from collections import OrderedDict
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from guillotina.profile import profilable
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
    _futures = None
    _uid = None
    _view_error = False
    _events = None

    application = None
    exc = None
    view_name = None
    found_view = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._futures = {}
        self._events = OrderedDict()
        self._initialized = time.time()

    def record(self, event_name):
        self._events[event_name] = time.time()

    def add_future(self, name, fut):
        if self._futures is None:
            self._futures = {}
        self._futures[name] = fut

    def get_future(self, name):
        try:
            return self._futures[name]
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
    def execute_futures(self):
        '''
        Should *not* be a coroutine since the deleting of
        the request object causes this to be canceled otherwise.
        '''
        if self._futures is None:
            return
        futures = []
        for fut in self._futures.values():
            if not asyncio.iscoroutine(fut):
                fut = fut()
            futures.append(fut)
        task = asyncio.ensure_future(asyncio.gather(*futures))
        self._futures = {}
        return task

    @property
    def uid(self):
        if self._uid is None:
            if 'X-FORWARDED-REQUEST-UID' in self.headers:
                self._uid = self.headers['X-FORWARDED-REQUEST-UID']
            else:
                self._uid = uuid.uuid4().hex
        return self._uid
