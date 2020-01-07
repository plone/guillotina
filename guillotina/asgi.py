from guillotina import glogging
from guillotina import task_vars
from guillotina.middlewares import ErrorsMiddleware
from guillotina.middlewares import ServiceExecutor
from guillotina.middlewares import TraversalRouter
from guillotina.request import Request
from guillotina.utils import apply_coroutine
from guillotina.utils import resolve_dotted_name

import asyncio
import enum
import inspect


logger = glogging.getLogger("guillotina")


class AppState(enum.IntEnum):

    STARTING = 0
    INITIALIZED = 1
    SHUTDOWN = 2


class AsgiApp:
    def __init__(self, config_file, settings, loop, router):
        self.config_file = config_file
        self.settings = settings
        self.loop = loop
        self.router = router
        # ...
        self.app = None
        self.on_cleanup = []
        self.state = AppState.STARTING

    def __call__(self, scope, receive=None, send=None):
        """
        ASGI callable compatible with versions 2 and 3
        """
        if receive is None or send is None:

            async def run_asgi2(receive, send):
                return await self.real_asgi_app(scope, receive, send)

            return run_asgi2
        else:
            return self.real_asgi_app(scope, receive, send)

    async def real_asgi_app(self, scope, receive, send):
        if scope["type"] == "http" or scope["type"] == "websocket":
            return await self.handler(scope, receive, send)

        elif scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await self.startup()
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await self.shutdown()
                    await send({"type": "lifespan.shutdown.complete"})
                    return

    async def startup(self):
        if self.state == AppState.INITIALIZED:
            return

        try:
            from guillotina.factory.app import startup_app

            self.loop = self.loop or asyncio.get_event_loop()

            self.app = await startup_app(
                config_file=self.config_file, settings=self.settings, loop=self.loop, server_app=self
            )
            self.next_app = self.build_middleware_stack(self.app.settings)
            self.server_settings = self.app.settings.get("server_settings", {})
            self.state = AppState.INITIALIZED
            return self.app
        except Exception:
            logger.exception("Something crashed during app startup")
            raise

    async def shutdown(self):
        if self.state == AppState.SHUTDOWN:
            return
        for clean in self.on_cleanup:
            await clean(self)
        self.state = AppState.SHUTDOWN

    def build_middleware_stack(self, settings):
        user_middlewares = [ErrorsMiddleware] + [
            resolve_dotted_name(m) for m in settings.get("middlewares", [])
        ]

        if TraversalRouter not in user_middlewares:
            # Add TraversalRouter at the end of the stack if it's not provided in the
            # configuration
            user_middlewares += [TraversalRouter]

        # The ServiceExecutor is the last middleware in the chain.
        last_middleware = ServiceExecutor()
        # We instantiate middlewares in reverse order
        for middleware in reversed(user_middlewares):
            args = inspect.getargspec(middleware).args
            if args[-1] == "handler":
                if "app" in args:
                    middleware = aiohttpHandler2asgi(middleware)
                else:
                    middleware = aiohttp2asgi(middleware)

            last_middleware = middleware(last_middleware)

        # The resuling stack would be:
        #    ErrorsMiddleware ->
        #      [user_middlewares] ->
        #        TraversalRouter (if not in user_middlewares) ->
        #          ServiceExecutor
        return last_middleware

    async def handler(self, scope, receive, send):
        # Ensure the ASGI server has initialized the server before sending a request
        # Some ASGI servers (i.e. daphne) doesn't implement the lifespan protocol.
        if not self.state == AppState.INITIALIZED:
            raise RuntimeError("The app is not initialized")

        if scope["type"] == "websocket":
            scope["method"] = "GET"

        request_settings = {k: v for k, v in self.server_settings.items() if k in ("client_max_size",)}
        request = Request.factory(scope, send, receive, **request_settings)
        task_vars.request.set(request)
        task_vars.app.set(self.app)

        resp = await self.next_app(scope, receive, send)

        if not resp.prepared:
            await resp.prepare(request)


def aiohttpHandler2asgi(aiohttp_handler):
    class AsgiMiddleware:
        def __init__(self, app):
            self.next_app = app

        async def __call__(self, scope, receive, send):
            request = task_vars.request.get()

            async def handler(request):
                return await self.next_app(scope, receive, send)

            aiohttp_middleware = await apply_coroutine(aiohttp_handler, self.next_app, handler)
            return await aiohttp_middleware(request)

    return AsgiMiddleware


def aiohttp2asgi(aiohttp_middleware):
    class AsgiMiddleware:
        def __init__(self, app):
            self.next_app = app

        async def __call__(self, scope, receive, send):
            request = task_vars.request.get()

            async def handler(request):
                return await self.next_app(scope, receive, send)

            return await aiohttp_middleware(request, handler)

    return AsgiMiddleware
