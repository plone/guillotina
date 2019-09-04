from zope.interface import Attribute
from zope.interface import Interface


class IRequest(Interface):
    url = Attribute("")
    path = Attribute("")
    method = Attribute("")
    resource = Attribute("traversed resource")
    tail = Attribute("")
    exc = Attribute("")
    found_view = Attribute("")
    view_name = Attribute("")

    def record(event_name) -> None:
        """
        record request event
        """


class ILanguage(Interface):
    pass


# Target interfaces on resolving


class IRenderer(Interface):
    pass


# Get Absolute URL


class IAbsoluteURL(Interface):
    pass


# Addon interface


class IAddOn(Interface):
    @classmethod
    def install(cls, container, request):  # noqa: N805
        """
        """

    @classmethod
    def uninstall(cls, container, request):  # noqa: N805
        """
        """
