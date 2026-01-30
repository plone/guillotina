from guillotina import configure
from guillotina._settings import app_settings
from guillotina.api.service import Service
from guillotina.auth import authenticate_user
from guillotina.auth.users import AnonymousUser
from guillotina.contrib.mcp.backend import clear_mcp_context
from guillotina.contrib.mcp.backend import set_mcp_context
from guillotina.contrib.mcp.server import get_mcp_app_and_server
from guillotina.interfaces import IResource
from guillotina.response import HTTPPreconditionFailed
from guillotina.response import HTTPUnauthorized
from guillotina.response import Response
from guillotina.utils import get_authenticated_user

import anyio
import copy
import logging


logger = logging.getLogger("guillotina")


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.mcp.Use",
    name="@mcp",
    summary="MCP protocol endpoint (POST)",
)
@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.mcp.Use",
    name="@mcp",
    summary="MCP protocol endpoint (GET)",
)
async def mcp_service(context, request):
    if not app_settings.get("mcp", {}).get("enabled", True):
        from guillotina.response import HTTPNotFound

        raise HTTPNotFound(content={"reason": "MCP is disabled"})
    set_mcp_context(context)
    try:
        scope = copy.copy(request.scope)
        scope["path"] = "/"
        scope["raw_path"] = b"/"
        app, server = get_mcp_app_and_server()
        session_manager = server.session_manager
        original_task_group = session_manager._task_group
        async with anyio.create_task_group() as tg:
            session_manager._task_group = tg
            try:
                await app(scope, request.receive, request.send)
            finally:
                session_manager._task_group = original_task_group
    finally:
        clear_mcp_context()
    resp = Response()
    resp._prepared = True
    resp._eof_sent = True
    return resp


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.mcp.IssueToken",
    name="@mcp-token",
    summary="Issue a long-lived JWT for MCP client configuration",
)
class MCPToken(Service):
    __body_required__ = False

    async def __call__(self):
        if not app_settings.get("mcp", {}).get("enabled", True):
            raise HTTPPreconditionFailed(content={"reason": "MCP is disabled"})
        user = get_authenticated_user()
        if user is None or isinstance(user, AnonymousUser):
            raise HTTPUnauthorized(content={"reason": "Authentication required"})
        try:
            body = await self.request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        duration_days = body.get("duration_days", 30)
        try:
            duration_days = int(duration_days)
        except (TypeError, ValueError):
            raise HTTPPreconditionFailed(
                content={"reason": "duration_days must be an integer", "value": duration_days}
            )
        mcp_settings = app_settings.get("mcp", {})
        max_days = mcp_settings.get("token_max_duration_days", 90)
        allowed = mcp_settings.get("token_allowed_durations")
        if allowed is not None:
            if duration_days not in allowed:
                raise HTTPPreconditionFailed(
                    content={
                        "reason": "duration_days must be one of",
                        "allowed": allowed,
                        "value": duration_days,
                    }
                )
        else:
            if duration_days < 1 or duration_days > max_days:
                raise HTTPPreconditionFailed(
                    content={
                        "reason": "duration_days must be between 1 and token_max_duration_days",
                        "token_max_duration_days": max_days,
                        "value": duration_days,
                    }
                )
        timeout = duration_days * 24 * 3600
        jwt_token, data = authenticate_user(user.id, data={"purpose": "mcp"}, timeout=timeout)
        return {
            "token": jwt_token,
            "exp": data["exp"],
            "duration_days": duration_days,
        }
