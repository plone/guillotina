from guillotina.db.orm.interfaces import IBaseObject
from guillotina.interfaces.content import IApplication
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Type
from yarl import URL
from zope.interface import Interface


class IRequest(Interface):
    url: URL
    path: str
    method: str
    resource: Optional[IBaseObject]
    tail: Optional[Tuple[str, ...]]
    exc: Optional[Exception]
    found_view: Optional[Type]
    view_name: Optional[str]
    application: Optional[IApplication]
    headers: Dict[str, str]
    uid: str

    def record(event_name) -> None:
        """
        record request event
        """

    async def json() -> Dict[str, Any]:
        ...


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
    def install(container, request):  # noqa: N805
        """
        """

    def uninstall(container, request):  # noqa: N805
        """
        """


class IIDChecker(Interface):
    def __init__(context):
        ...

    async def __call__(id_: str, type_: str) -> bool:
        ...
