from aiohttp.streams import EmptyStreamReader
from guillotina.request import GuillotinaRequest
import asyncio
import os
import yaml


def headers_to_list(headers):
    return [[k.encode(), v.encode()] for k, v in headers.items()]


class AsgiStreamReader(EmptyStreamReader):
    """Dummy implementation of StreamReader"""

    def __init__(self, receive):
        self.receive = receive
        self.finished = False
        self._buffer = b""

    async def readany(self):
        return await self.read()

    async def read(self):
        if self.finished:
            return b""
        payload = await self.receive()
        self.finished = not payload.get("more_body", False)
        return payload["body"]

    async def readexactly(self, n: int) -> bytes:
        data = b""

        if self._buffer:
            data += self._buffer[:n]
            self._buffer = self._buffer[n:]  # rest

        while len(data) < n and not self.finished:
            chunk = await self.read()
            data += chunk

        if len(data) < n:
            raise asyncio.IncompleteReadError(data, n)

        self._buffer += data[n:]
        return data


class AsgiStreamWriter():
    """Dummy implementation of StreamWriter"""

    buffer_size = 0
    output_size = 0
    length = 0  # type: Optional[int]

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

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" or scope["type"] == "websocket":
            # daphne is not sending `lifespan` event
            if not self.app:
                self.app = await self.startup()
            return await self.handler(scope, receive, send)

        elif scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    self.app = await self.startup()
                    await send({'type': 'lifespan.startup.complete'})
                elif message['type'] == 'lifespan.shutdown':
                    await self.shutdown()
                    await send({'type': 'lifespan.shutdown.complete'})
                    return

    async def startup(self):
        from guillotina.factory.app import startup_app
        return await startup_app(
            config_file=self.config_file,
            settings=self.settings, loop=self.loop, server_app=self)

    async def shutdown(self):
        pass

    async def handler(self, scope, receive, send):
        # Aiohttp compatible StreamReader
        payload = AsgiStreamReader(receive)

        if scope["type"] == "websocket":
            scope["method"] = "GET"

        request = GuillotinaRequest(
            scope["scheme"],
            scope["method"],
            scope["path"],
            scope["headers"],
            payload,
            loop=self.loop,
            send=send,
            scope=scope,
            receive=receive
        )

        # This is to fake IRequest interface
        request.record = lambda x: None

        route = await self.app.router.resolve(request)
        resp = await route.handler(request)

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


# from guillotina.factory.app import make_asgi_app

# # asgi app singleton
# app = make_asgi_app()
