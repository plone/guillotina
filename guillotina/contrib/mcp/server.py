from guillotina._settings import app_settings
from guillotina.contrib.mcp.backend import InProcessBackend
from guillotina.contrib.mcp.tools import register_tools


_mcp_server = None
_mcp_app = None


def get_mcp_app_and_server():
    global _mcp_server, _mcp_app
    if _mcp_app is not None:
        return _mcp_app, _mcp_server
    from mcp.server.fastmcp import FastMCP

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
    _mcp_server = mcp
    _mcp_app = mcp.streamable_http_app()
    return _mcp_app, _mcp_server
