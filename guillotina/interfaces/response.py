from multidict import CIMultiDict
from typing import Union
from zope.interface import Attribute
from zope.interface import Interface


class IResponse(Interface):
    status_code = Attribute("status code")
    content = Attribute("content")
    headers = Attribute("headers")

    def __init__(
        *,
        body: bytes = None,
        content: dict = None,
        headers: Union[dict, CIMultiDict] = None,
        status: int = None,
        content_type: str = None,
        content_length: int = None,
    ):
        """
        """

    def set_body(body):
        """
        """
