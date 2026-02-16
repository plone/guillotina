from guillotina._settings import app_settings
from guillotina.contrib.mcp.backend import InProcessBackend
from guillotina.contrib.mcp.interfaces import IMCPUtility
from guillotina.contrib.mcp.tools import register_tools
from zope.interface import implementer


@implementer(IMCPUtility)
class MCPUtility:
    async def initialize(self, app):
        pass

    async def finalize(self, app):
        pass

    def __init__(self, settings=None):
        from mcp.server.fastmcp import FastMCP

        settings = settings or {}
        backend = InProcessBackend()
        mcp = FastMCP(
            "Guillotina MCP",
            json_response=True,
            stateless_http=True,
        )
        if hasattr(mcp, "settings") and hasattr(mcp.settings, "streamable_http_path"):
            mcp.settings.streamable_http_path = "/"
        register_tools(mcp, backend)
        extra_module = app_settings.get("mcp", {}).get("extra_tools_module")
        if extra_module:
            mod = __import__(str(extra_module), fromlist=["register_extra_tools"])
            getattr(mod, "register_extra_tools")(mcp, backend)
        self._server = mcp
        self._app = mcp.streamable_http_app()

    @property
    def server(self):
        return self._server

    @property
    def app(self):
        return self._app
