from guillotina import configure
from guillotina._settings import app_settings
from guillotina.api.service import Service
from guillotina.auth import authenticate_user
from guillotina.auth.users import AnonymousUser
from guillotina.component import get_utility
from guillotina.contrib.mcp.backend import clear_mcp_context
from guillotina.contrib.mcp.backend import set_mcp_context
from guillotina.contrib.mcp.interfaces import IMCPUtility
from guillotina.interfaces import IResource
from guillotina.response import HTTPPreconditionFailed
from guillotina.response import HTTPUnauthorized
from guillotina.response import Response
from guillotina.utils import get_authenticated_user
from multidict import CIMultiDict

import anyio
import copy
import json
import logging


logger = logging.getLogger("guillotina")


def _ensure_mcp_enabled():
    if not app_settings.get("mcp", {}).get("enabled", True):
        from guillotina.response import HTTPNotFound

        raise HTTPNotFound(content={"reason": "MCP is disabled"})


def _make_dummy_response() -> Response:
    resp = Response()
    resp._prepared = True
    resp._eof_sent = True
    return resp


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.mcp.Use",
    name="@mcp",
    summary="MCP protocol endpoint (POST, captured response)",
)
@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.mcp.Use",
    name="@mcp",
    summary="MCP protocol endpoint (GET, captured response)",
)
async def mcp_service(context, request):
    _ensure_mcp_enabled()
    set_mcp_context(context)
    try:
        scope = copy.copy(request.scope)
        scope["path"] = "/"
        scope["raw_path"] = b"/"
        mcp_utility = get_utility(IMCPUtility)

        response_status = 200
        response_headers = []
        response_body = bytearray()

        async def capture_send(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status", 200)
                response_headers[:] = list(message.get("headers", []))
                return
            if message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    response_body.extend(body)

        await mcp_utility.session_manager.handle_request(scope, request.receive, capture_send)

        headers = CIMultiDict()
        for key, value in response_headers:
            header_key = key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
            header_value = value.decode() if isinstance(value, (bytes, bytearray)) else str(value)
            headers.add(header_key, header_value)

        return Response(body=bytes(response_body), headers=headers, status=response_status)
    finally:
        clear_mcp_context()


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.mcp.Use",
    name="@mcp-legacy",
    summary="MCP protocol endpoint (POST, passthrough dummy response)",
)
@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.mcp.Use",
    name="@mcp-legacy",
    summary="MCP protocol endpoint (GET, passthrough dummy response)",
)
async def mcp_legacy_service(context, request):
    _ensure_mcp_enabled()
    set_mcp_context(context)
    try:
        from mcp.server.streamable_http import StreamableHTTPServerTransport

        scope = copy.copy(request.scope)
        scope["path"] = "/"
        scope["raw_path"] = b"/"
        mcp_utility = get_utility(IMCPUtility)

        http_transport = StreamableHTTPServerTransport(
            mcp_session_id=None,
            is_json_response_enabled=True,
            event_store=None,
            security_settings=None,
        )

        async def run_stateless_server(*, task_status: anyio.abc.TaskStatus[None] = anyio.TASK_STATUS_IGNORED):
            async with http_transport.connect() as streams:
                read_stream, write_stream = streams
                task_status.started()
                try:
                    await mcp_utility.server.run(
                        read_stream,
                        write_stream,
                        mcp_utility.server.create_initialization_options(),
                        stateless=True,
                    )
                except Exception:
                    logger.exception("Legacy stateless MCP session crashed")

        async with anyio.create_task_group() as tg:
            await tg.start(run_stateless_server)
            await http_transport.handle_request(scope, request.receive, request.send)
            await http_transport.terminate()

        return _make_dummy_response()
    finally:
        clear_mcp_context()


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
        except (json.JSONDecodeError, ValueError):
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
