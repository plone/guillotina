from aiohttp import web_request
from collections import OrderedDict
from guillotina import task_vars
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from guillotina.interfaces.content import IApplication
from guillotina.profile import profilable
from guillotina.utils import execute
from typing import Dict
from typing import Optional
from zope.interface import implementer

import time
import uuid


@implementer(IRequest, IDefaultLayer)
class Request(web_request.Request):
    """
    Guillotina specific request type.
    We store potentially a lot of state onto the request
    object as it is essential our poor man's thread local model
    """

    #    tail = None
    #    resource = None
    #    security = None

    _uid = None
    _view_error = False
    _events: dict = {}

    application: Optional[IApplication] = None
    exc = None
    view_name = None
    found_view = None
    resource: Optional[IBaseObject] = None
    tail = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._events = OrderedDict()
        self._initialized = time.time()
        #: Dictionary of matched path parameters on request
        self.matchdict: Dict[str, str] = {}

    def record(self, event_name: str):
        """
        Record event on the request

        :param event_name: name of event
        """
        self._events[event_name] = time.time()

    def add_future(self, *args, **kwargs):
        """
        Register a future to be executed after the request has finished.

        :param name: name of future
        :param fut: future to execute after request
        :param scope: group the futures to execute different groupings together
        :param args: arguments to execute future with
        :param kwargs: kwargs to execute future with
        """
        execute.add_future(*args, **kwargs)

    def get_future(self, name: str, scope: str = ""):
        """
        Get a registered future

        :param name: scoped futures to execute. Leave default for normal behavior
        :param scope: scope name the future was registered for
        """
        return execute.get_future(name, scope)

    @property
    def events(self):
        return self._events

    @property
    def view_error(self):
        return self._view_error

    @profilable
    def execute_futures(self, scope: str = ""):
        """
        Execute all the registered futures in a new task

        :param scope: scoped futures to execute. Leave default for normal behavior
        """
        return execute.execute_futures(scope)

    def clear_futures(self):
        execute.clear_futures()

    @property
    def uid(self):
        if self._uid is None:
            if "X-FORWARDED-REQUEST-UID" in self.headers:
                self._uid = self.headers["X-FORWARDED-REQUEST-UID"]
            else:
                self._uid = uuid.uuid4().hex
        return self._uid

    def __enter__(self):
        task_vars.request.set(self)

    def __exit__(self, *args):
        """
        contextvars already tears down to previous value, do not set to None here!
        """

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, *args):
        return self.__exit__()
