from typing import Any
from typing import Coroutine
from typing import List
from typing import Optional
from typing import Union
from zope.interface import Interface


class IMailer(Interface):
    """ """

    def __init__(settings):
        pass

    async def initialize(app):
        pass

    async def send(
        self,
        recipient: Union[List[str], str],
        subject: Any = None,
        message: Any = None,
        text: Any = None,
        html: Any = None,
        sender: Any = None,
        message_id: Any = None,
        endpoint: Any = "default",
        priority: Any = 3,
        attachments: Any = None,
        cc: Optional[Union[List[str], str]] = None,
    ) -> Coroutine[Any, Any, Any]:
        pass


class IMailEndpoint(Interface):
    def __init__():
        pass

    def from_settings(settings):
        """
        setup the endpoint from settings
        """

    async def send(sender, recipients, message, retry=False):
        pass
