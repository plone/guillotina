from guillotina import schema
from zope.interface import Interface


class IMCPSettings(Interface):
    enabled = schema.Bool(title="Enable MCP services", default=True, required=False)
    server_name = schema.TextLine(title="Low-level MCP server name", default="guillotina-mcp", required=False)
    default_child_limit = schema.Int(title="Default list_children limit", default=50, required=False)


class IMCPToolRegistry(Interface):
    def list_tools():
        """Return registered MCP tools."""

    async def invoke(tool_name, context, request, arguments=None):
        """Execute one tool and return a JSON-serializable response."""

    def metadata():
        """Return metadata for diagnostics."""

    def invalidate_cache(reason="manual"):
        """Invalidate cached tool responses."""

    def create_lowlevel_server(context=None, request=None):
        """Build a low-level MCP server object."""
