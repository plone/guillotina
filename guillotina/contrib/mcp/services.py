from guillotina import configure
from guillotina.api.service import Service
from guillotina.component import query_utility
from guillotina.contrib.mcp.interfaces import IMCPToolRegistry
from guillotina.interfaces import IResource
from guillotina.response import HTTPBadRequest
from guillotina.response import HTTPServiceUnavailable


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
        return {"mcp": registry.metadata(), "tools": registry.list_tools()}


@configure.service(
    method="GET",
    context=IResource,
    name="@mcp/tools",
    permission="guillotina.MCPView",
    summary="List available MCP tools",
    allow_access=True,
)
class MCPToolsService(Service):
    async def __call__(self):
        registry = _get_registry()
        return {"tools": registry.list_tools()}


@configure.service(
    method="POST",
    context=IResource,
    name="@mcp/tools/invoke",
    permission="guillotina.MCPExecute",
    summary="Execute one registered MCP tool",
    allow_access=True,
)
class MCPInvokeToolService(Service):
    async def __call__(self):
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
    method="GET",
    context=IResource,
    name="@mcp/server/status",
    permission="guillotina.MCPView",
    summary="Check whether low-level MCP server dependencies are available",
    allow_access=True,
)
class MCPServerStatusService(Service):
    async def __call__(self):
        registry = _get_registry()
        metadata = registry.metadata()
        try:
            registry.create_lowlevel_server(context=self.context, request=self.request)
        except RuntimeError as exc:
            return {"ready": False, "error": str(exc), "mcp": metadata}
        return {"ready": True, "mcp": metadata}
