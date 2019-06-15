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
        self.loop = None

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

    async def startup(self, settings=None, loop=None):
        # The config file is defined in the env var `CONFIG`
        loop = loop or asyncio.get_event_loop()
        from guillotina.factory import make_app
        import guillotina
        self.loop = loop

        config = os.getenv("CONFIG", None)
        if settings:
            pass
        elif not config:
            settings = guillotina._settings.default_settings
        else:
            with open(config, "r") as f:
                settings = yaml.load(f, Loader=yaml.FullLoader)
        return await make_app(settings=settings, loop=loop, server_app=self)

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
            await send(
                {
                    "type": "http.response.start",
                    "status": resp.status,
                    "headers": headers_to_list(resp.headers)
                }
            )

            body = resp.text or ""
            await send({"type": "http.response.body", "body": body.encode()})


from guillotina.factory.app import make_asgi_app
# asgi app singleton
app = make_asgi_app()
