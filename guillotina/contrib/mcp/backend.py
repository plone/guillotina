import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

from guillotina import app_settings
from guillotina.contrib.mcp import resources as mcp_resources
from guillotina.contrib.mcp import tools
from guillotina.contrib.redis import get_driver


ToolHandler = Callable[[Any, Any, Dict[str, Any]], Awaitable[Dict[str, Any]]]
ResourceHandler = Callable[[Any], Awaitable[Dict[str, Any]]]
logger = logging.getLogger("guillotina.contrib.redis")


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: ToolHandler
    cacheable: bool = False


@dataclass
class MCPResource:
    name: str
    uri: str
    description: str
    endpoint: str
    handler: ResourceHandler
    mime_type: str = "application/json"


class MCPToolRegistry:
    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        config = app_settings.get("mcp", {})
        self._settings = settings or {}
        self._enabled = bool(config.get("enabled", True))
        self._server_name = str(config.get("server_name", "guillotina-mcp"))
        self._default_child_limit = int(config.get("default_child_limit", 50))
        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, MCPResource] = {}
        self._register_default_tools()
        self._register_default_resources()
        self._key_cache_redis_prefix = "mcp_tool_cache:v1"

    async def initialize(self, app):
        self._cache_disabled = True
        self._driver_redis = None
        try:
            self._driver_redis = await get_driver()
            self._cache_disabled = False
        except Exception:
            logger.info("redis not enabled to cache")

    def _register_default_tools(self) -> None:
        for (
            tool_name,
            description,
            input_schema,
            handler,
            cacheable,
        ) in tools.default_tools(self._default_child_limit):
            self.register_tool(
                name=tool_name,
                description=description,
                input_schema=input_schema,
                handler=handler,
                cacheable=cacheable,
            )

    def _register_default_resources(self) -> None:
        for (
            name,
            uri,
            description,
            endpoint,
            handler,
        ) in mcp_resources.default_resources():
            self.register_resource(
                name=name,
                uri=uri,
                description=description,
                endpoint=endpoint,
                handler=handler,
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

    # ── Resource management ──────────────────────────────────────────

    def register_resource(
        self,
        *,
        name: str,
        uri: str,
        description: str,
        endpoint: str,
        handler: ResourceHandler,
        mime_type: str = "application/json",
    ) -> None:
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("Resource name is required")
        self._resources[clean_name] = MCPResource(
            name=clean_name,
            uri=str(uri or "").strip(),
            description=str(description or "").strip(),
            endpoint=str(endpoint or "").strip(),
            handler=handler,
            mime_type=mime_type,
        )

    def list_resources(self) -> List[Dict[str, Any]]:
        return [
            {
                "uri": res.uri,
                "name": res.name,
                "description": res.description,
                "endpoint": res.endpoint,
                "mimeType": res.mime_type,
            }
            for res in sorted(self._resources.values(), key=lambda r: r.name)
        ]

    async def read_resource(self, resource_name: str, context: Any, request: Any) -> Dict[str, Any]:
        clean_name = str(resource_name or "").strip()
        if clean_name not in self._resources:
            raise ValueError(f"Unknown MCP resource: {resource_name}")
        resource = self._resources[clean_name]
        return await resource.handler(request)

    def _cache_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        payload = json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"{self._key_cache_redis_prefix}:{tool_name}:{digest[:16]}"

    def _serialize_cache_value(self, value: Dict[str, Any]) -> str:
        return json.dumps(value, separators=(",", ":"), sort_keys=True)

    def _deserialize_cache_value(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        if isinstance(value, str):
            return json.loads(value)
        return value

    async def invoke(
        self,
        tool_name: str,
        context: Any,
        request: Any,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clean_name = str(tool_name or "").strip()
        if clean_name not in self._tools:
            raise ValueError(f"Unknown MCP tool: {tool_name}")

        clean_arguments = arguments or {}
        if not isinstance(clean_arguments, dict):
            raise ValueError("Tool arguments must be an object")

        tool = self._tools[clean_name]
        cache_key = self._cache_key(clean_name, clean_arguments)
        if tool.cacheable and self._cache_disabled is False:
            result = await self._driver_redis.get(cache_key)
            if result is not None:
                return self._deserialize_cache_value(result)
        result = await tool.handler(context, request, clean_arguments)
        if tool.cacheable and self._cache_disabled is False:
            # Expire in 1 hour
            await self._driver_redis.set(
                key=cache_key,
                data=self._serialize_cache_value(result),
                expire=3600,
            )
        return result

    async def invalidate_cache(self, reason: str = "manual") -> None:
        if self._cache_disabled is False:
            keys_to_delete = await self._driver_redis.keys_startswith(self._key_cache_redis_prefix)
            await self._driver_redis.delete_all(keys_to_delete)

    def metadata(self) -> Dict[str, Any]:
        return {
            "enabled": self.is_enabled(),
            "server_name": self._server_name,
            "tool_count": len(self._tools),
            "resource_count": len(self._resources),
        }

    def create_lowlevel_server(self, context: Any = None, request: Any = None) -> Any:
        from guillotina.contrib.mcp.server import LowLevelMCPServer

        adapter = LowLevelMCPServer(
            registry=self,
            context=context,
            request=request,
            server_name=self._server_name,
        )
        return adapter.build()
