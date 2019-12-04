from zope.interface import Attribute
from zope.interface import Interface


class IResponse(Interface):
    status_code = Attribute("status code")
    content = Attribute("content")
    headers = Attribute("headers")

    def __init__(*, content: dict = None, headers: dict = None, status: int = None):
        """
        """


class IASGIResponse(Interface):
    """
    Mark ASGI server responses with interface
    """
