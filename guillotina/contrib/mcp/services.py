from guillotina import configure
from guillotina.api.service import Service
from guillotina.component import query_utility
from guillotina.contrib.mcp.interfaces import IMCPToolRegistry
from guillotina.contrib.mcp.security import require_access_content
from guillotina.interfaces import IResource
from guillotina.response import HTTPMethodNotAllowed, HTTPNotFound, HTTPServiceUnavailable, Response


_MCP_PROTOCOL_POST_METHODS = ["POST"]


def _reject_non_post_protocol(context, request, method: str):
    action = request.matchdict.get("action", "")
    if action != "protocol":
        raise HTTPNotFound(content={"reason": f"Unknown MCP {method} action: {action}"})
    require_access_content(context)
    if method == "DELETE":
        reason = "MCP endpoint does not support session termination"
    else:
        reason = "MCP endpoint does not offer an SSE stream"
    raise HTTPMethodNotAllowed(
        method,
        _MCP_PROTOCOL_POST_METHODS,
        content={"reason": reason},
    )


def _get_registry():
    registry = query_utility(IMCPToolRegistry)
    if registry is None:
        raise HTTPServiceUnavailable(content={"reason": "MCP registry utility is not available"})
    if not registry.is_enabled():
        raise HTTPServiceUnavailable(content={"reason": "MCP integration is disabled"})
    return registry


@configure.service(
    method="POST",
    context=IResource,
    name="@mcp/{action}",
    permission="guillotina.MCPExecute",
    summary="MCP Streamable HTTP protocol endpoint (JSON-RPC 2.0)",
    allow_access=True,
)
class MCPActionPostService(Service):
    async def __call__(self):
        require_access_content(self.context)
        action = self.request.matchdict.get("action", "")
        if action == "protocol":
            return await self._handle_protocol()
        raise HTTPNotFound(content={"reason": f"Unknown MCP POST action: {action}"})

    async def _handle_protocol(self):
        try:
            import anyio
            from mcp.server.streamable_http import StreamableHTTPServerTransport
        except ImportError as exc:
            raise HTTPServiceUnavailable(
                content={"reason": 'MCP SDK missing. Install "guillotina[mcp]".'}
            ) from exc

        registry = _get_registry()
        transport = StreamableHTTPServerTransport(
            mcp_session_id=None,
            is_json_response_enabled=True,
        )
        server_obj = registry.create_lowlevel_server(context=self.context, request=self.request)
        init_options = server_obj.create_initialization_options()

        async with transport.connect() as (read_stream, write_stream):
            async with anyio.create_task_group() as tg:
                tg.start_soon(
                    server_obj.run,
                    read_stream,
                    write_stream,
                    init_options,
                    False,  # raise_exceptions
                    True,  # stateless — allows each request to be handled independently
                )
                await transport.handle_request(
                    self.request.scope,
                    self.request.receive,
                    self.request.send,
                )
                tg.cancel_scope.cancel()

        # Response was already written directly to the ASGI socket by the transport.
        # Return a pre-marked Response so Guillotina does not write an extra response.
        resp = Response(status=200)
        resp._prepared = True
        resp._eof_sent = True
        return resp


@configure.service(
    method="GET",
    context=IResource,
    name="@mcp/{action}",
    permission="guillotina.MCPExecute",
    summary="MCP Streamable HTTP GET is not offered (JSON-only)",
    allow_access=True,
)
class MCPActionGetService(Service):
    async def __call__(self):
        _reject_non_post_protocol(self.context, self.request, "GET")


@configure.service(
    method="DELETE",
    context=IResource,
    name="@mcp/{action}",
    permission="guillotina.MCPExecute",
    summary="MCP Streamable HTTP session termination is not offered",
    allow_access=True,
)
class MCPActionDeleteService(Service):
    async def __call__(self):
        _reject_non_post_protocol(self.context, self.request, "DELETE")
