from guillotina import glogging
from guillotina import task_vars
from guillotina.exceptions import ConflictError
from guillotina.exceptions import TIDConflictError
from guillotina.request import Request
from guillotina.response import ASGISimpleResponse


logger = glogging.getLogger("guillotina")


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
                if message["type"] == "lifespan.startup":
                    await self.startup()
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await self.shutdown()
                    await send({"type": "lifespan.shutdown.complete"})
                    return

    async def startup(self):
        from guillotina.factory.app import startup_app

        self.app = await startup_app(
            config_file=self.config_file, settings=self.settings, loop=self.loop, server_app=self
        )
        return self.app

    async def shutdown(self):
        for clean in self.on_cleanup:
            await clean(self)

    async def handler(self, scope, receive, send):
        if scope["type"] == "websocket":
            scope["method"] = "GET"

        request = Request.factory(scope, send, receive)
        task_vars.request.set(request)
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
        resp = await self.request_handler(request)

        if not resp.prepared:
            await resp.prepare(request)

        return resp

    async def request_handler(self, request, retries=0):
        try:
            route = await self.app.router.resolve(request)
            return await route.handler(request)

        except (ConflictError, TIDConflictError) as e:
            if self.settings.get("conflict_retry_attempts", 3) > retries:
                label = "DB Conflict detected"
                if isinstance(e, TIDConflictError):
                    label = "TID Conflict Error detected"
                tid = getattr(getattr(request, "_txn", None), "_tid", "not issued")
                logger.debug(f"{label}, retrying request, tid: {tid}, retries: {retries + 1})", exc_info=True)
                request._retry_attempt = retries + 1
                request.clear_futures()
                return await self.request_handler(request, retries + 1)
            else:
                logger.error(
                    "Exhausted retry attempts for conflict error on tid: {}".format(
                        getattr(getattr(request, "_txn", None), "_tid", "not issued")
                    )
                )
                return ASGISimpleResponse(body=b"", status=409)
