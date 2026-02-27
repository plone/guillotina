from zope.interface import Attribute
from zope.interface import Interface


class IMCPUtility(Interface):
    """MCP utility providing low-level server and session manager."""

    server = Attribute("Low-level MCP server instance")
    session_manager = Attribute("Streamable HTTPSessionManager instance")


class IMCPToolProvider(Interface):
    """Named utility that exposes one MCP tool."""

    def get_tool_definition():
        """Return dict with name, description and input_schema."""

    async def execute(arguments):
        """Execute tool call and return dict."""


class IMCPDescriptionExtras(Interface):
    """Utility returning a dict mapping tool name to extra description text
    (appended to the base tool description for LLM context).
    Tool names: search, count, get_content, list_children.
    """
