from zope.interface import Interface

from guillotina import schema


class IMCPSettings(Interface):
    enabled = schema.Bool(title="Enable MCP services", default=True, required=False)
    server_name = schema.TextLine(title="Low-level MCP server name", default="guillotina-mcp", required=False)
    default_child_limit = schema.Int(title="Default list_children limit", default=50, required=False)


class IMCPToolRegistry(Interface):
    def list_tools():
        """Return registered MCP tools."""

    def list_resources():
        """Return registered MCP resources."""

    async def invoke(tool_name, context, request, arguments=None):
        """Execute one tool and return a JSON-serializable response."""

    async def read_resource(resource_name, context, request):
        """Read one resource and return a JSON-serializable response."""

    def metadata():
        """Return metadata for diagnostics."""

    async def invalidate_cache(reason="manual"):
        """Invalidate cached tool responses."""

    def create_lowlevel_server(context=None, request=None):
        """Build a low-level MCP server object."""


class IMCPAuthPolicy(Interface):
    def is_enabled(request, context):
        """Return whether this policy applies to the current MCP request."""

    def unauthorized_headers(request, context):
        """Return extra headers for an unauthenticated MCP protocol response."""

    def is_authorized(request, context):
        """Return whether the current authenticated request may use this MCP endpoint."""
