from guillotina import error_reasons
from guillotina import logger
from guillotina import response
from guillotina import task_vars
from guillotina._settings import app_settings
from guillotina.browser import View
from guillotina.i18n import default_message_factory as _
from guillotina.traversal import apply_rendering

import asyncio
import traceback
import uuid


class ErrorsMiddleware:
    def __init__(self, app):
        self.next_app = app

    async def __call__(self, scope, receive, send):
        headers_sent = False

        async def _send(msg):
            nonlocal headers_sent
            headers_sent = True
            await send(msg)

        try:
            resp = await self.next_app(scope, receive, _send)
        except Exception as exc:
            request = task_vars.request.get()
            view_result = self.generate_error_response(exc, None, "ServiceError")
            resp = await apply_rendering(View(None, request), request, view_result)
            if headers_sent:
                # Too late to send status 500, headers already sent
                raise
        return resp

    def generate_error_response(self, e, request, error, status=500):
        # We may need to check the roles of the users to show the real error
        eid = uuid.uuid4().hex
        if isinstance(e, asyncio.CancelledError):  # pragma: no cover
            message = _("Cancelled execution of view") + " " + eid
            logger.warning(message, exc_info=e, eid=eid, request=request)
        else:
            message = _("Error on execution of view") + " " + eid
            logger.error(message, exc_info=e, eid=eid, request=request)
        data = {
            "message": message,
            "reason": error_reasons.UNKNOWN.name,
            "details": error_reasons.UNKNOWN.details,
            "eid": eid,
        }
        if app_settings.get("debug"):
            data["traceback"] = traceback.format_exc()
        return response.HTTPInternalServerError(content=data)
