from aiohttp.streams import EmptyStreamReader
from guillotina import glogging
from guillotina import task_vars
from guillotina.exceptions import ConflictError
from guillotina.exceptions import TIDConflictError
from guillotina.request import Request
from typing import Optional

import asyncio


logger = glogging.getLogger('guillotina')


def headers_to_list(headers):
    return [[k.encode(), v.encode()] for k, v in headers.items()]


class AsgiStreamReader(EmptyStreamReader):
    """Dummy implementation of StreamReader"""

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


class AsgiStreamWriter():
    """Dummy implementation of StreamWriter"""

    buffer_size = 0
    output_size = 0
    length: Optional[int] = 0

    def __init__(self, send):
        self.send = send
        self._buffer = asyncio.Queue()
        self.eof = False

    async def write(self, chunk: bytes) -> None:
        """Write chunk into stream."""
        await self._buffer.put(chunk)

    async def write_eof(self, chunk: bytes=b'') -> None:
        """Write last chunk."""
        await self.write(chunk)
        self.eof = True
        await self.drain()

    async def drain(self) -> None:
        """Flush the write buffer."""
        while not self._buffer.empty():
            body = await self._buffer.get()
            await self.send({
                "type": "http.response.body",
                "body": body,
                "more_body": True
            })

        if self.eof:
            await self.send({
                "type": "http.response.body",
                "body": b"",
                "more_body": False
            })

    def enable_compression(self, encoding: str='deflate') -> None:
        """Enable HTTP body compression"""
        raise NotImplemented()

    def enable_chunking(self) -> None:
        """Enable HTTP chunked mode"""
        raise NotImplemented()


class AsgiApp:
    def __init__(self, config_file, settings, loop):
        self.app = None
        self.config_file = config_file
        self.settings = settings
        self.loop = loop
        self.on_cleanup = []
        self.route = None

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" or scope["type"] == "websocket":
            return await self.handler(scope, receive, send)

        elif scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    await self.startup()
                    await send({'type': 'lifespan.startup.complete'})
                elif message['type'] == 'lifespan.shutdown':
                    await self.shutdown()
                    await send({'type': 'lifespan.shutdown.complete'})
                    return

    async def startup(self):
        from guillotina.factory.app import startup_app
        self.app = await startup_app(
            config_file=self.config_file,
            settings=self.settings, loop=self.loop, server_app=self)
        return self.app

    async def shutdown(self):
        for clean in self.on_cleanup:
            await clean(self)

    async def handler(self, scope, receive, send):
        # Aiohttp compatible StreamReader
        payload = AsgiStreamReader(receive)

        if scope["type"] == "websocket":
            scope["method"] = "GET"

        request = Request(
            scope["scheme"],
            scope["method"],
            scope["path"],
            scope["query_string"],
            scope["headers"],
            payload,
            loop=self.loop,
            send=send,
            scope=scope,
            receive=receive
        )

        task_vars.request.set(request)
        resp = await self.request_handler(request)

        # WS handling after view execution missing here!!!
        if scope["type"] != "websocket":
            from guillotina.response import StreamResponse

            if not isinstance(resp, StreamResponse):
                await send(
                    {
                        "type": "http.response.start",
                        "status": resp.status,
                        "headers": headers_to_list(resp.headers)
                    }
                )
                body = resp.text or ""
                await send({"type": "http.response.body", "body": body.encode()})

    async def request_handler(self, request, retries=0):
        try:
            route = await self.app.router.resolve(request)
            return await route.handler(request)

        except (ConflictError, TIDConflictError) as e:
            if self.settings.get('conflict_retry_attempts', 3) > retries:
                label = 'DB Conflict detected'
                if isinstance(e, TIDConflictError):
                    label = 'TID Conflict Error detected'
                tid = getattr(getattr(request, '_txn', None), '_tid', 'not issued')
                logger.debug(
                    f'{label}, retrying request, tid: {tid}, retries: {retries + 1})',
                    exc_info=True)
                request._retry_attempt = retries + 1
                request.clear_futures()
                return await self.request_handler(request, retries + 1)
            else:
                logger.error(
                    'Exhausted retry attempts for conflict error on tid: {}'.format(
                        getattr(getattr(request, '_txn', None), '_tid', 'not issued')
                    ))
                from guillotina.response import HTTPConflict
                return HTTPConflict()
