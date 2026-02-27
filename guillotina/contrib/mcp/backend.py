from dataclasses import dataclass
from guillotina import app_settings
from guillotina.contrib.mcp import tools
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

import json


ToolHandler = Callable[[Any, Any, Dict[str, Any]], Awaitable[Dict[str, Any]]]


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: ToolHandler
    cacheable: bool = False


class MCPToolRegistry:
    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        config = app_settings.get("mcp", {})
        self._settings = settings or {}
        self._enabled = bool(config.get("enabled", True))
        self._server_name = str(config.get("server_name", "guillotina-mcp"))
        self._default_child_limit = int(config.get("default_child_limit", 50))
        self._tools: Dict[str, MCPTool] = {}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_revision = 0
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        for tool_name, description, input_schema, handler, cacheable in tools.default_tools(
            self._default_child_limit
        ):
            self.register_tool(
                name=tool_name,
                description=description,
                input_schema=input_schema,
                handler=handler,
                cacheable=cacheable,
            )

    def is_enabled(self) -> bool:
        return self._enabled

    def register_tool(
        self,
        *,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: ToolHandler,
        cacheable: bool = False,
    ) -> None:
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("Tool name is required")
        self._tools[clean_name] = MCPTool(
            name=clean_name,
            description=str(description or "").strip(),
            input_schema=input_schema or {"type": "object"},
            handler=handler,
            cacheable=cacheable,
        )

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
                "cacheable": tool.cacheable,
            }
            for tool in sorted(self._tools.values(), key=lambda registered: registered.name)
        ]

    def _cache_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        payload = json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)
        return f"{tool_name}:{payload}"

    async def invoke(
        self, tool_name: str, context: Any, request: Any, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        clean_name = str(tool_name or "").strip()
        if clean_name not in self._tools:
            raise ValueError(f"Unknown MCP tool: {tool_name}")

        clean_arguments = arguments or {}
        if not isinstance(clean_arguments, dict):
            raise ValueError("Tool arguments must be an object")

        tool = self._tools[clean_name]
        cache_key = self._cache_key(clean_name, clean_arguments)
        if tool.cacheable and cache_key in self._cache:
            return self._cache[cache_key]

        result = await tool.handler(context, request, clean_arguments)
        if tool.cacheable:
            self._cache[cache_key] = result
        return result

    def invalidate_cache(self, reason: str = "manual") -> None:
        self._cache.clear()
        self._cache_revision += 1

    def metadata(self) -> Dict[str, Any]:
        return {
            "enabled": self.is_enabled(),
            "server_name": self._server_name,
            "tool_count": len(self._tools),
            "cache_revision": self._cache_revision,
        }

    def create_lowlevel_server(self, context: Any = None, request: Any = None) -> Any:
        from guillotina.contrib.mcp.server import LowLevelMCPServer

        adapter = LowLevelMCPServer(
            registry=self, context=context, request=request, server_name=self._server_name
        )
        return adapter.build()
