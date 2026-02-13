from zope.interface import Attribute
from zope.interface import Interface


class IMCPUtility(Interface):
    """MCP server utility providing the FastMCP app and server instances."""

    server = Attribute("FastMCP server instance")
    app = Attribute("ASGI app from streamable_http_app()")


class IMCPDescriptionExtras(Interface):
    """Utility returning a dict mapping tool name to extra description text
    (appended to the base tool description for LLM context).
    Tool names: search, count, get_content, list_children.
    """
