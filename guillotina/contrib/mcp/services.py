from guillotina import configure
from guillotina._settings import app_settings
from guillotina.contrib.mcp.backend import clear_mcp_context
from guillotina.contrib.mcp.backend import set_mcp_context
from guillotina.contrib.mcp.server import get_mcp_asgi_app
from guillotina.contrib.mcp.server import get_mcp_server_instance
from guillotina.interfaces import IResource
from guillotina.response import Response

import anyio
import copy
import logging


logger = logging.getLogger("guillotina")

_mcp_asgi_app = None


def _get_mcp_app():
    global _mcp_asgi_app
    if _mcp_asgi_app is None:
        _mcp_asgi_app = get_mcp_asgi_app()
    return _mcp_asgi_app


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
        app = _get_mcp_app()
        server = get_mcp_server_instance()
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
