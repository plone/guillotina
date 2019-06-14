from aiohttp.test_utils import make_mocked_request
from aiohttp.streams import EmptyStreamReader
import asyncio
import multidict
import guillotina
import os
import yaml


def headers_to_list(headers):
    return [[k.encode(), v.encode()] for k, v in headers.items()]


class AsgiStreamReader(EmptyStreamReader):
    """Dummy implementation of StreamReader"""

    def __init__(self, receive):
        self.receive = receive
        self.finished = False

    async def readany(self):
        return await self.read()

    async def read(self):
        if self.finished:
            return b""
        payload = await self.receive()
        self.finished = True
        return payload["body"]


class AsgiApp:
    def __init__(self):
        self.app = None

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # daphne is not sending `lifespan` event
            if not self.app:
                self.app = await self.setup()
            return await self.handler(scope, receive, send)

        elif scope["type"] == "lifespan":
            self.app = await self.setup()

    async def setup(self, settings=None, loop=None):
        # The config file is defined in the env var `CONFIG`
        loop = asyncio.get_event_loop()
        from guillotina.factory import make_app

        config = os.getenv("CONFIG", None)
        if settings:
            pass
        elif not config:
            settings = guillotina._settings.default_settings
        else:
            with open(config, "r") as f:
                settings = yaml.load(f, Loader=yaml.FullLoader)
        return await make_app(settings=settings, loop=loop, server_app=self)

    async def handler(self, scope, receive, send):
        # Copy headers
        headers = multidict.CIMultiDict()
        raw_headers = scope["headers"]
        for key, value in raw_headers:
            headers.add(key.decode(), value.decode())

        method = scope["method"]
        path = scope["path"]

        # Aiohttp compatible StreamReader
        payload = AsgiStreamReader(receive)

        request = make_mocked_request(method, path, headers=headers, payload=payload)

        # This is to fake IRequest interface
        request.record = lambda x: None
        request.__class__ = guillotina.request.Request

        route = await self.app.router.resolve(request)
        resp = await route.handler(request)

        await send(
            {
                "type": "http.response.start",
                "status": resp.status,
                "headers": headers_to_list(resp.headers)
            }
        )

        if resp.text:
            body = resp.text.encode()
        else:
            body = b""

        await send({"type": "http.response.body", "body": body})


# asgi app singleton
app = AsgiApp()
