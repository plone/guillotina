from typing import Any

import importlib
import json


class LowLevelMCPServer:
    def __init__(
        self, *, registry: Any, context: Any = None, request: Any = None, server_name: str = "guillotina-mcp"
    ):
        self.registry = registry
        self.context = context
        self.request = request
        self.server_name = server_name

    def _load_lowlevel_modules(self):
        try:
            lowlevel = importlib.import_module("mcp.server.lowlevel")
            types_module = importlib.import_module("mcp.types")
        except ImportError as exc:
            raise RuntimeError(
                'Low-level MCP SDK is missing. Install it with `pip install "guillotina[mcp]"`.'
            ) from exc
        return lowlevel, types_module

    def _build_tool_type(self, types_module: Any, tool_data: Any) -> Any:
        try:
            return types_module.Tool(
                name=tool_data["name"],
                description=tool_data["description"],
                inputSchema=tool_data["inputSchema"],
            )
        except TypeError:
            return types_module.Tool(
                name=tool_data["name"],
                description=tool_data["description"],
                input_schema=tool_data["inputSchema"],
            )

    def _build_resource_type(self, types_module: Any, resource_data: Any) -> Any:
        from pydantic import AnyUrl

        uri_str = resource_data["uri"]
        try:
            uri = AnyUrl(uri_str)
        except Exception:
            uri = uri_str  # type: ignore[assignment]
        try:
            return types_module.Resource(
                uri=uri,
                name=resource_data["name"],
                description=resource_data.get("description", ""),
                mimeType=resource_data.get("mimeType", "application/json"),
            )
        except TypeError:
            return types_module.Resource(
                uri=uri,
                name=resource_data["name"],
                description=resource_data.get("description", ""),
                mime_type=resource_data.get("mimeType", "application/json"),
            )

    def _build_text_content_type(self, types_module: Any, text: str) -> Any:
        try:
            return types_module.TextContent(type="text", text=text)
        except TypeError:
            return types_module.TextContent(text=text)

    def build(self) -> Any:
        lowlevel, types_module = self._load_lowlevel_modules()
        server = lowlevel.Server(self.server_name)

        @server.list_tools()
        async def handle_list_tools():
            return [
                self._build_tool_type(types_module, tool_data) for tool_data in self.registry.list_tools()
            ]

        @server.list_resources()
        async def handle_list_resources():
            return [
                self._build_resource_type(types_module, res_data)
                for res_data in self.registry.list_resources()
            ]

        @server.read_resource()
        async def handle_read_resource(uri: Any) -> str:
            if self.context is None or self.request is None:
                raise ValueError("Context and request are required to read Guillotina MCP resources")
            uri_str = str(uri)
            for res in self.registry.list_resources():
                if res["uri"] == uri_str:
                    data = await self.registry.read_resource(res["name"], self.context, self.request)
                    return json.dumps(data, ensure_ascii=True, sort_keys=True, default=str)
            raise ValueError(f"Unknown resource URI: {uri}")

        @server.call_tool()
        async def handle_call_tool(name: str, arguments: Any):
            if self.context is None or self.request is None:
                raise ValueError("Context and request are required to execute Guillotina MCP tools")
            result = await self.registry.invoke(name, self.context, self.request, arguments or {})
            payload = json.dumps(result, ensure_ascii=True, sort_keys=True, default=str)
            return [self._build_text_content_type(types_module, payload)]

        return server
