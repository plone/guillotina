from aiohttp.web_ws import WSMessage
from aiohttp.web import WSMsgType
from aiohttp.helpers import reify
from collections import OrderedDict
from guillotina import task_vars
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from guillotina.profile import profilable
from guillotina.utils import execute
from typing import Any, Awaitable, Callable, Dict, Generic, Iterator, Tuple, TypeVar, Optional
from yarl import URL
from zope.interface import implementer

import asyncio
import enum
import json
import time
import multidict
import uuid
import urllib.parse


_T = TypeVar('_T')


class State(enum.Enum):
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2


class WebSocketDisconnect(Exception):
    def __init__(self, code):
        self.code = code


class WebSocketException(Exception):
    pass


class WebSocketJsonDecodeError(WebSocketException):
    pass


class WebSocketMsg:
    # Type constants
    TEXT = "text"
    BYTES = "bytes"

    def __init__(self, msg):
        self.msg = msg

    @property
    def type(self):
        if "bytes" in self.msg and self.msg["bytes"]:
            return WebSocketMsg.BYTES
        else:
            return WebSocketMsg.TEXT

    @property
    def json(self):
        try:
            if self.type == WebSocketMsg.TEXT:
                return json.loads(self.msg["text"])
            else:
                return json.loads(self.msg["bytes"])
        except json.JSONDecodeError:
            raise WebSocketJsonDecodeError()

    @property
    def text(self):
        return self.msg["text"]

    @property
    def bytes(self):
        return self.msg["bytes"]

    def __str__(self):
        if self.msg.type == WebSocketMsg.TEXT:
            return f"[TEXT]: {self.text[:15]}..."
        else:
            return f"[BYTES]: {self.bytes[:15]}..."


class GuillotinaWebSocket:
    def __init__(self, scope, send, receive):
        self.scope = scope
        self._receive = receive
        self._send = send
        self.in_state = State.CONNECTING
        self.out_state = State.CONNECTING

    async def prepare(self, request=None):
        return await self.accept()

    async def send_str(self, data):
        return await self.send_text(data)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.out_state == State.DISCONNECTED:
            raise StopAsyncIteration()

        try:
            msg = await self.receive()
        except WebSocketDisconnect:
            # Close the ws connection
            await self.close()
            raise StopAsyncIteration()
        return WebSocketMsg(msg)

    async def receive(self):
        if self.in_state == State.CONNECTING:
            msg = await self._receive()
            msg_type = msg["type"]
            if msg_type != "websocket.connect":
                raise WebSocketException(f"msg_type {msg_type} not allowed in state {self.in_state}")
            self.in_state = State.CONNECTED
            return msg
        elif self.in_state == State.CONNECTED:
            msg = await self._receive()
            msg_type = msg["type"]
            if msg_type not in ["websocket.receive", "websocket.disconnect"]:
                raise WebSocketException(f"msg_type {msg_type} not allowed in state {self.in_state}")

            if msg_type == "websocket.disconnect":
                self.in_state = State.DISCONNECTED
            return msg
        else:
            raise RuntimeError("channel is already closed")

    async def send(self, msg):
        if self.out_state == State.CONNECTING:
            msg_type = msg["type"]
            if msg_type not in ["websocket.accept", "websocket.close"]:
                raise WebSocketException(f"msg_type {msg_type} not allowed in state {self.out_state}")
            if msg_type == "websocket.accept":
                self.out_state = State.CONNECTED
            else:
                self.out_state = State.DISCONNECTED
            await self._send(msg)
        elif self.out_state == State.CONNECTED:
            msg_type = msg["type"]
            if msg_type not in ["websocket.send", "websocket.close"]:
                raise WebSocketException(f"msg_type {msg_type} not allowed in state {self.out_state}")

            if msg_type == "websocket.close":
                self.out_state = State.DISCONNECTED
            await self._send(msg)
        else:
            raise RuntimeError("channel is already closed")

    async def receive_text(self):
        if self.in_state != State.CONNECTED:
            raise WebSocketException(f"receive is not allowed in state {self.in_state}")

        msg = await self.receive()
        if msg["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(msg["code"])
        return msg["text"]

    async def send_text(self, data):
        await self.send({"type": "websocket.send", "text": data})

    async def accept(self, subprotocol=None):
        # Wait for the connect message
        if self.in_state == State.CONNECTING:
            await self.receive()
        await self.send({"type": "websocket.accept", "subprotocol": subprotocol})

    async def close(self, code=1000):
        await self.send({"type": "websocket.close", "code": code})


class AsyncStreamIterator(Generic[_T]):

    def __init__(self, read_func: Callable[[], Awaitable[_T]]) -> None:
        self.read_func = read_func

    def __aiter__(self) -> 'AsyncStreamIterator[_T]':
        return self

    async def __anext__(self) -> _T:
        rv = await self.read_func()
        if rv == b'':
            raise StopAsyncIteration  # NOQA
        return rv


class AsgiStreamReader():
    def __init__(self, receive):
        self.finished = False
        self._asgi_receive = receive
        self._buffer = b""

    async def readany(self):
        from guillotina.files import CHUNK_SIZE
        return await self.read(CHUNK_SIZE)

    async def readexactly(self, n: int) -> bytes:
        data = await self.read(n)
        if len(data) < n:
            raise asyncio.IncompleteReadError(data, n)
        return data

    async def read(self, n: int = -1):
        if self._buffer:
            data = self._buffer
        else:
            data = b""

        while (n == -1 or len(data) < n) and not self.finished:
            chunk = await self.receive()
            data += chunk

        if n == -1:
            self._buffer = None
            return data
        else:
            req_chunk, rest = data[:n], data[n:]
            self._buffer = rest
            return req_chunk

    async def receive(self):
        payload = await self._asgi_receive()
        self.finished = not payload.get("more_body", False)
        return payload["body"]

    def __aiter__(self) -> AsyncStreamIterator[bytes]:
        return AsyncStreamIterator(self.readany)  # type: ignore


@implementer(IRequest, IDefaultLayer)
class Request(object):
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

    application = None
    exc = None
    view_name = None
    found_view = None

    def __init__(self, scheme, method, path, query_string, raw_headers,
                 stream_reader, client_max_size: int=1024**2, loop=None,
                 send=None, receive=None, scope=None):
        self.send = send
        self._initialized = time.time()
        self.receive = receive
        self.scope = scope
        self._scheme = scheme
        self._loop = loop
        self._method = method
        self._raw_path = path
        self._query_string = query_string
        self._rel_url = URL(path)
        self._raw_headers = raw_headers
        self._stream_reader = stream_reader

        self._client_max_size = client_max_size

        self.charset = None
        self.content_type = None

        self._read_bytes: Optional[bytes] = None
        self._state: Dict[str, Any] = {}
        self._cache: Dict[Any, Any] = {}
        self._futures: dict = {}
        self._events = OrderedDict()
        self._initialized = time.time()
        #: Dictionary of matched path parameters on request
        self.matchdict: Dict[str, str] = {}

    def get_ws(self):
        return GuillotinaWebSocket(self.scope,
                                   receive=self.receive,
                                   send=self.send)

    def record(self, event_name: str):
        '''
        Record event on the request

        :param event_name: name of event
        '''
        self._events[event_name] = time.time()

    def add_future(self, *args, **kwargs):
        '''
        Register a future to be executed after the request has finished.

        :param name: name of future
        :param fut: future to execute after request
        :param scope: group the futures to execute different groupings together
        :param args: arguments to execute future with
        :param kwargs: kwargs to execute future with
        '''
        execute.add_future(*args, **kwargs)

    def get_future(self, name: str, scope: str=''):
        '''
        Get a registered future

        :param name: scoped futures to execute. Leave default for normal behavior
        :param scope: scope name the future was registered for
        '''
        return execute.get_future(name, scope)

    @property
    def events(self):
        return self._events

    @property
    def view_error(self):
        return self._view_error

    @profilable
    def execute_futures(self, scope: str=''):
        '''
        Execute all the registered futures in a new task

        :param scope: scoped futures to execute. Leave default for normal behavior
        '''
        return execute.execute_futures(scope)

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

    def __enter__(self):
        task_vars.request.set(self)

    def __exit__(self, *args):
        '''
        contextvars already tears down to previous value, do not set to None here!
        '''

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, *args):
        return self.__exit__()

    @reify
    def rel_url(self):
        return self._rel_url

    # MutableMapping API

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._state[key] = value

    def __delitem__(self, key: str) -> None:
        del self._state[key]

    def __len__(self) -> int:
        return len(self._state)

    def __iter__(self) -> Iterator[str]:
        return iter(self._state)

    @reify
    def scheme(self):
        return self._scheme

    @reify
    def method(self) -> str:
        """Read only property for getting HTTP method.

        The value is upper-cased str like 'GET', 'POST', 'PUT' etc.
        """
        return self._method

    @reify
    def version(self) -> Tuple[int, int]:
        """Read only property for getting HTTP version of request.

        Returns aiohttp.protocol.HttpVersion instance.
        """
        return self.scope["http_version"]

    @reify
    def host(self) -> str:
        """Hostname of the request.
        """
        return self.headers.get("host")

    @reify
    def url(self):
        url = URL.build(scheme=self.scheme, host=self.host)
        return url.join(self._rel_url)

    @reify
    def path(self) -> str:
        """The URL including *PATH INFO* without the host or scheme.

        E.g., ``/app/blog``
        """
        return self._raw_path

    @reify
    def query(self) -> 'multidict.CIMultiDict[str]':
        """A multidict with all the variables in the query string."""
        query = urllib.parse.parse_qsl(self._query_string.decode("utf-8"))
        return multidict.CIMultiDict(query)

    @reify
    def query_string(self) -> str:
        """The query string in the URL.

        E.g., id=10
        """
        return self._query_string

    @reify
    def headers(self) -> 'multidict.CIMultiDict[str]':
        """A case-insensitive multidict proxy with all headers."""
        return multidict.CIMultiDict(
            [(k.decode(), v.decode()) for k, v in self._raw_headers]
        )

    @reify
    def raw_headers(self):
        """A sequence of pairs for all headers."""
        return self._raw_headers

    @reify
    def content(self):
        """Return raw payload stream."""
        return self._stream_reader

    @property
    def can_read_body(self) -> bool:
        """Return True if request's HTTP BODY can be read, False otherwise."""
        return not self._stream_reader.at_eof()

    async def release(self) -> None:
        """Release request.

        Eat unread part of HTTP BODY if present.
        """
        while not self._stream_reader.at_eof():
            await self._stream_reader.readany()

    async def read(self) -> bytes:
        """Read request body if present.

        Returns bytes object with full request content.
        """
        if self._read_bytes is None:
            body = bytearray()
            while True:
                chunk = await self._stream_reader.readany()
                body.extend(chunk)
                if self._client_max_size:
                    body_size = len(body)
                    if body_size >= self._client_max_size:
                        from guillotina.response import HTTPRequestEntityTooLarge
                        raise HTTPRequestEntityTooLarge(
                            max_size=self._client_max_size,
                            actual_size=body_size
                        )
                if not chunk:
                    break
            self._read_bytes = bytes(body)
        return self._read_bytes

    async def text(self) -> str:
        """Return BODY as text using encoding from .charset."""
        bytes_body = await self.read()
        encoding = self.charset or 'utf-8'
        return bytes_body.decode(encoding)

    async def json(self, *, loads=json.loads) -> Any:  # type: ignore
        """Return BODY as JSON."""
        body = await self.text()
        return loads(body)

    def __repr__(self) -> str:
        ascii_encodable_path = self.path.encode('ascii', 'backslashreplace') \
            .decode('ascii')
        return "<{} {} {} >".format(self.__class__.__name__,
                                    self._method, ascii_encodable_path)

    def __eq__(self, other: object) -> bool:
        return id(self) == id(other)

    async def _prepare_hook(self, response):
        return
