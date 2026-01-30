from guillotina._settings import app_settings
from guillotina.contrib.mcp.backend import InProcessBackend
from guillotina.contrib.mcp.tools import register_tools

_mcp_server_instance = None


def get_mcp_server(backend=None):
    from mcp.server.fastmcp import FastMCP

    if backend is None:
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
    return mcp


def get_mcp_server_instance():
    return _mcp_server_instance


def get_mcp_asgi_app(backend=None):
    global _mcp_server_instance
    server = get_mcp_server(backend)
    app = server.streamable_http_app()
    _mcp_server_instance = server
    return app
