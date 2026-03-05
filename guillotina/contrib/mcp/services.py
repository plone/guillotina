from guillotina import configure
from guillotina.api.service import Service
from guillotina.component import query_utility
from guillotina.contrib.mcp.interfaces import IMCPToolRegistry
from guillotina.interfaces import IResource
from guillotina.response import HTTPBadRequest
from guillotina.response import HTTPNotFound
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
        return {
            "mcp": registry.metadata(),
            "tools": registry.list_tools(),
            "resources": registry.list_resources(),
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
            return {"tools": registry.list_tools()}
        if action == "resources":
            registry = _get_registry()
            return {"resources": registry.list_resources()}
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
