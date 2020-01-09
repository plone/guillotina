from guillotina import logger
from guillotina import task_vars
from guillotina._settings import app_settings
from guillotina.exc_resp import HTTPConflict
from guillotina.exceptions import ConflictError
from guillotina.exceptions import TIDConflictError


class TraversalRouter:
    """
    This middleware is responsible of doing traversal and executing the service.
    """

    def __init__(self, router):
        self.router = router

    async def __call__(self, scope, receive, send):
        request = task_vars.request.get()
        return await self.request_handler(request)

    async def request_handler(self, request, retries=0):
        try:
            route = await self.router.resolve(request)
            resp = await route.handler(request)
            return resp

        except (ConflictError, TIDConflictError) as e:
            if app_settings.get("conflict_retry_attempts", 3) > retries:
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
