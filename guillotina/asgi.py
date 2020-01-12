from guillotina import glogging
from guillotina import task_vars
from guillotina.exc_resp import HTTPConflict
from guillotina.exceptions import ConflictError
from guillotina.exceptions import TIDConflictError
from guillotina.middlewares import ErrorsMiddleware
from guillotina.request import Request
from guillotina.utils import resolve_dotted_name

import asyncio
import enum


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

        # Guillotina is the last middleware in the chain
        last_middleware = Guillotina(self.app, self.router)
        for middleware in reversed(user_middlewares):
            last_middleware = middleware(last_middleware)
        return last_middleware

    async def handler(self, scope, receive, send):
        # Ensure the ASGI server has initialized the server before sending a request
        # Some ASGI servers (i.e. daphne) doesn't implement the lifespan protocol.
        if not self.state == AppState.INITIALIZED:
            raise RuntimeError("The app is not initialized")

        if scope["type"] == "websocket":
            scope["method"] = "GET"

        resp = await self.next_app(scope, receive, send)

        if not resp.prepared:
            request = task_vars.request.get()
            await resp.prepare(request)

        return


class Guillotina:
    def __init__(self, asgi_app, router):
        self.asgi_app = asgi_app
        self.router = router

    async def __call__(self, scope, receive, send):
        request_settings = {
            k: v for k, v in self.asgi_app.server_settings.items() if k in ("client_max_size",)
        }
        request = Request.factory(scope, send, receive, **request_settings)
        task_vars.request.set(request)

        resp = await self.request_handler(request)

        return resp

    async def request_handler(self, request, retries=0):
        try:
            route = await self.router.resolve(request)
            resp = await route.handler(request)
            return resp

        except (ConflictError, TIDConflictError) as e:
            if self.asgi_app.settings.get("conflict_retry_attempts", 3) > retries:
                label = "DB Conflict detected"
                if isinstance(e, TIDConflictError):
                    label = "TID Conflict Error detected"
                tid = getattr(getattr(request, "_txn", None), "_tid", "not issued")
                logger.debug(f"{label}, retrying request, tid: {tid}, retries: {retries + 1})", exc_info=True)
                request._retry_attempt = retries + 1
                request.clear_futures()
                for var in (
                    "txn",
                    "tm",
                    "futures",
                    "authenticated_user",
                    "security_policies",
                    "container",
                    "registry",
                    "db",
                ):
                    # and make sure to reset various task vars...
                    getattr(task_vars, var).set(None)
                return await self.request_handler(request, retries + 1)
            else:
                logger.error(
                    "Exhausted retry attempts for conflict error on tid: {}".format(
                        getattr(getattr(request, "_txn", None), "_tid", "not issued")
                    )
                )
                raise HTTPConflict()
