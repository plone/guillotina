from guillotina.component import get_utilities_for
from guillotina.component import query_utility
from guillotina.contrib.mcp.interfaces import IMCPToolProvider
from guillotina.contrib.mcp.interfaces import IMCPUtility
from zope.interface import implementer

import json
import typing


@implementer(IMCPUtility)
class MCPUtility:
    async def initialize(self, app):
        pass

    async def finalize(self, app):
        pass

    def __init__(self, settings=None):
        from mcp.server.lowlevel.server import Server
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        import mcp.types as types

        server = Server(
            "Guillotina MCP",
        )

        @server.list_tools()
        async def _list_tools():
            tools = []
            for name, provider in sorted(get_utilities_for(IMCPToolProvider), key=lambda value: value[0]):
                definition = provider.get_tool_definition() or {}
                tool_name = definition.get("name") or name
                tools.append(
                    types.Tool(
                        name=tool_name,
                        description=definition.get("description", ""),
                        inputSchema=definition.get("input_schema") or {"type": "object", "properties": {}},
                    )
                )
            return tools

        @server.call_tool()
        async def _call_tool(name: str, arguments: typing.Optional[typing.Dict[str, typing.Any]]):
            provider = query_utility(IMCPToolProvider, name=name)
            if provider is None:
                raise ValueError(f"Unknown tool: {name}")
            result = await provider.execute(arguments or {})
            if not isinstance(result, dict):
                raise TypeError(f"Invalid result for {name}: {type(result).__name__}")
            text = json.dumps(result, indent=2, ensure_ascii=False)
            return [types.TextContent(type="text", text=text)]

        self._server = server
        self._session_manager = StreamableHTTPSessionManager(
            app=server,
            json_response=True,
            stateless=True,
        )

    @property
    def server(self):
        return self._server

    @property
    def session_manager(self):
        return self._session_manager
