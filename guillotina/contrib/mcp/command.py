from guillotina.commands import Command
from guillotina.contrib.mcp.backend import HttpBackend
from guillotina.contrib.mcp.server import get_mcp_server

import argparse
import asyncio
import logging
import os


logger = logging.getLogger("guillotina")


class MCPServerCommand(Command):
    description = "Run MCP server (out-of-process) that connects to Guillotina via REST."

    def get_parser(self):
        parser = super(MCPServerCommand, self).get_parser()
        parser.add_argument("--base-url", help="Guillotina base URL (e.g. http://localhost:8080)")
        parser.add_argument("--username", help="Basic auth username")
        parser.add_argument("--password", help="Basic auth password")
        parser.add_argument("--host", default="0.0.0.0", help="MCP server host")
        parser.add_argument("--port", type=int, default=8000, help="MCP server port")
        return parser

    async def run(self, arguments, settings, app):
        mcp_settings = settings.get("mcp", {})
        auth = mcp_settings.get("auth", {})
        base_url = (
            getattr(arguments, "base_url", None)
            or mcp_settings.get("base_url")
            or os.environ.get("MCP_GUILLOTINA_BASE_URL")
        )
        username = (
            getattr(arguments, "username", None)
            or auth.get("username")
            or os.environ.get("MCP_GUILLOTINA_USERNAME", "root")
        )
        password = (
            getattr(arguments, "password", None)
            or auth.get("password")
            or os.environ.get("MCP_GUILLOTINA_PASSWORD", "")
        )
        if not base_url:
            logger.error("base_url is required (config mcp.base_url, --base-url, or MCP_GUILLOTINA_BASE_URL)")
            return
        backend = HttpBackend(base_url=base_url, username=username, password=password)
        server = get_mcp_server(backend)
        host = getattr(arguments, "host", "0.0.0.0")
        port = getattr(arguments, "port", 8000)

        def run_server():
            server.run(transport="streamable-http", host=host, port=port)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_server)
