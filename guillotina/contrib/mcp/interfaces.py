from zope.interface import Interface


class IMCPDescriptionExtras(Interface):
    """Callable utility returning a dict mapping tool name to extra description text (appended to the base tool description for LLM context). Tool names: search, count, get_content, list_children."""
