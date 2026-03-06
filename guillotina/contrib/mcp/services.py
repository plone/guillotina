from guillotina import configure
from guillotina.api.service import Service
from guillotina.component import query_utility
from guillotina.contrib.mcp.interfaces import IMCPToolRegistry
from guillotina.interfaces import IResource
from guillotina.response import HTTPBadRequest
from guillotina.response import HTTPNotFound
from guillotina.response import HTTPServiceUnavailable
from guillotina.response import Response


def _get_registry():
    registry = query_utility(IMCPToolRegistry)
    if registry is None:
        raise HTTPServiceUnavailable(content={"reason": "MCP registry utility is not available"})
    return registry


@configure.service(
    method="GET",
    context=IResource,
    name="@mcp",
    permission="guillotina.MCPView",
    summary="Inspect MCP integration status and metadata",
    allow_access=True,
)
class MCPInfoService(Service):
    async def __call__(self):
        registry = _get_registry()
        base = self.request.path.rstrip("/")
        return {
            "mcp": registry.metadata(),
            "tools": registry.list_tools(),
            "resources": registry.list_resources(),
            "usage": {
                "protocol": {
                    "description": (
                        "Native MCP Streamable HTTP endpoint (JSON-RPC 2.0). "
                        "Send initialize then tools/call or resources/read."
                    ),
                    "method": "POST",
                    "url": f"{base}/protocol",
                    "headers": {
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream",
                    },
                    "body_example": {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/list",
                        "params": {},
                    },
                },
                "invoke_tool": {
                    "method": "POST",
                    "url": f"{base}/tools/invoke",
                    "body": {"tool": "<tool_name>", "arguments": {}},
                    "description": "Guillotina-specific REST shortcut to invoke a tool directly.",
                },
                "read_resource": {
                    "method": "GET",
                    "url": f"{base}/resources/<resource_name>",
                    "description": "GET this URL replacing <resource_name> with a name from the resources list.",
                },
            },
        }


@configure.service(
    method="GET",
    context=IResource,
    name="@mcp/{action}",
    permission="guillotina.MCPView",
    summary="MCP sub-actions (tools, resources, server)",
    allow_access=True,
)
class MCPActionGetService(Service):
    async def __call__(self):
        action = self.request.matchdict.get("action", "")
        if action == "tools":
            registry = _get_registry()
            base = self.request.path.rstrip("/").rsplit("/", 1)[0]
            return {
                "tools": registry.list_tools(),
                "invoke": {
                    "method": "POST",
                    "url": f"{base}/tools/invoke",
                    "body": {"tool": "<tool_name>", "arguments": {}},
                },
            }
        if action == "resources":
            registry = _get_registry()
            base = self.request.path.rstrip("/").rsplit("/", 1)[0]
            return {
                "resources": registry.list_resources(),
                "read": {
                    "method": "GET",
                    "url": f"{base}/resources/<resource_name>",
                    "description": "Replace <resource_name> with the 'name' field of any listed resource.",
                },
            }
        if action == "protocol":
            base = self.request.path.rstrip("/")
            return {
                "description": "MCP Streamable HTTP endpoint (JSON-RPC 2.0, MCP spec compliant).",
                "method": "POST",
                "url": base,
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
                "lifecycle": [
                    {
                        "step": 1,
                        "method": "initialize",
                        "description": "Handshake and capability negotiation",
                    },
                    {"step": 2, "method": "tools/list", "description": "Discover available tools"},
                    {"step": 3, "method": "tools/call", "description": "Invoke a tool"},
                    {"step": 4, "method": "resources/list", "description": "Discover available resources"},
                    {"step": 5, "method": "resources/read", "description": "Read a resource by URI"},
                ],
            }
        raise HTTPNotFound(content={"reason": f"Unknown MCP action: {action}"})


@configure.service(
    method="GET",
    context=IResource,
    name="@mcp/{action}/{sub}",
    permission="guillotina.MCPView",
    summary="MCP sub-resource endpoints",
    allow_access=True,
)
class MCPSubActionGetService(Service):
    async def __call__(self):
        action = self.request.matchdict.get("action", "")
        sub = self.request.matchdict.get("sub", "")

        if action == "server" and sub == "status":
            return await self._server_status()

        if action == "resources":
            # Dispatch to the registered resource by name
            registry = _get_registry()
            try:
                return await registry.read_resource(sub, self.context, self.request)
            except ValueError:
                raise HTTPNotFound(content={"reason": f"Unknown MCP resource: {sub}"})

        raise HTTPNotFound(content={"reason": f"Unknown MCP endpoint: {action}/{sub}"})

    async def _server_status(self):
        registry = _get_registry()
        metadata = registry.metadata()
        try:
            registry.create_lowlevel_server(context=self.context, request=self.request)
        except RuntimeError as exc:
            return {"ready": False, "error": str(exc), "mcp": metadata}
        return {"ready": True, "mcp": metadata}


@configure.service(
    method="POST",
    context=IResource,
    name="@mcp/{action}/{sub}",
    permission="guillotina.MCPExecute",
    summary="MCP tool invocation",
    allow_access=True,
)
class MCPSubActionPostService(Service):
    async def __call__(self):
        action = self.request.matchdict.get("action", "")
        sub = self.request.matchdict.get("sub", "")
        key = f"{action}/{sub}"

        if key == "tools/invoke":
            return await self._invoke_tool()
        raise HTTPNotFound(content={"reason": f"Unknown MCP POST endpoint: {key}"})

    async def _invoke_tool(self):
        registry = _get_registry()
        try:
            payload = await self.request.json()
        except Exception as exc:
            raise HTTPBadRequest(content={"reason": "Invalid JSON payload"}) from exc

        if not isinstance(payload, dict):
            raise HTTPBadRequest(content={"reason": "Invalid payload: expected object"})

        tool_name = payload.get("tool")
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise HTTPBadRequest(content={"reason": "Tool name is required"})

        arguments = payload.get("arguments", {})
        if not isinstance(arguments, dict):
            raise HTTPBadRequest(content={"reason": "Tool arguments must be an object"})

        try:
            result = await registry.invoke(tool_name, self.context, self.request, arguments)
        except ValueError as exc:
            raise HTTPBadRequest(content={"reason": str(exc)}) from exc

        return {"tool": tool_name, "result": result}


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
