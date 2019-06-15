from aiohttp.web_ws import WSMessage
from aiohttp.web import StreamResponse, WSMsgType
from aiohttp.helpers import reify
from guillotina.request import Request
from starlette.websockets import WebSocket, WebSocketDisconnect
from typing import Any, Iterator, Tuple
from yarl import URL

import multidict
import json
import urllib.parse


class GuillotinaWebSocket:
    def __init__(self, scope, send, receive):
        self.ws = WebSocket(scope,
                            receive=receive,
                            send=send)

    async def prepare(self, request):
        return await self.ws.accept()

    async def close(self):
        return await self.ws.close()

    async def send_str(self, data):
        return await self.ws.send_text(data)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            msg = await self.ws.receive_text()
        except WebSocketDisconnect:
            # Close the ws connection
            await self.close()
            raise StopAsyncIteration()
        return WSMessage(WSMsgType.TEXT, msg, '')


class GuillotinaRequest(Request):

    def __init__(self, scheme, method, path, query_string, raw_headers,
                 payload, client_max_size: int=1024**2, loop=None,
                 send=None, receive=None, scope=None):
        self.send = send
        self.receive = receive
        self.scope = scope
        self._scheme = scheme
        self._loop = loop
        self._method = method
        self._raw_path = path
        self._query_string = query_string
        self._rel_url = URL(path)
        self._raw_headers = raw_headers
        self._payload = payload

        self._client_max_size = client_max_size

        self._read_bytes = None
        self._state = {}
        self._cache = {}

    def get_ws(self):
        return GuillotinaWebSocket(self.scope,
                                   receive=self.receive,
                                   send=self.send)

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
        return self._version

    @reify
    def host(self) -> str:
        """Hostname of the request.

        Hostname is resolved in this order:

        - overridden value by .clone(host=new_host) call.
        - HOST HTTP header
        - socket.getfqdn() value
        """
        host = self.headers.get("host")
        return host

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
    def query(self) -> 'MultiDictProxy[str]':
        """A multidict with all the variables in the query string."""

        l = urllib.parse.parse_qsl(self._query_string.decode("utf-8"))
        return multidict.CIMultiDict(l)

    @reify
    def query_string(self) -> str:
        """The query string in the URL.

        E.g., id=10
        """
        return self._query_string

    @reify
    def headers(self) -> 'CIMultiDictProxy[str]':
        """A case-insensitive multidict proxy with all headers."""
        headers = multidict.CIMultiDict()
        # TODO: extend
        for key, value in self._raw_headers:
            headers.add(key.decode(), value.decode())
        self._headers = headers
        return headers

    @reify
    def raw_headers(self):
        """A sequence of pairs for all headers."""
        return self._raw_headers

    @reify
    def content(self):
        """Return raw payload stream."""
        return self._payload

    @property
    def has_body(self) -> bool:
        """Return True if request's HTTP BODY can be read, False otherwise."""
        warnings.warn(
            "Deprecated, use .can_read_body #2005",
            DeprecationWarning, stacklevel=2)
        return not self._payload.at_eof()

    @property
    def can_read_body(self) -> bool:
        """Return True if request's HTTP BODY can be read, False otherwise."""
        return not self._payload.at_eof()

    @reify
    def body_exists(self) -> bool:
        """Return True if request has HTTP BODY, False otherwise."""
        return type(self._payload) is not EmptyStreamReader

    async def release(self) -> None:
        """Release request.

        Eat unread part of HTTP BODY if present.
        """
        while not self._payload.at_eof():
            await self._payload.readany()

    async def read(self) -> bytes:
        """Read request body if present.

        Returns bytes object with full request content.
        """
        if self._read_bytes is None:
            body = bytearray()
            while True:
                chunk = await self._payload.readany()
                body.extend(chunk)
                if self._client_max_size:
                    body_size = len(body)
                    if body_size >= self._client_max_size:
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

    async def json(self, *, loads=json.loads) -> Any:
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

    async def _prepare_hook(self, response: StreamResponse) -> None:
        return
