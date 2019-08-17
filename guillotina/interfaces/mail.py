from zope.interface import Interface


class IMailer(Interface):
    """
    """

    def __init__(settings):
        pass

    async def initialize(app):
        pass

    def send(recipient=None, subject=None, message=None, text=None, html=None, sender=None):
        pass

    def send_immediately(
        recipient=None,
        subject=None,
        message=None,
        text=None,
        html=None,
        sender=None,
        fail_silently=False,
    ):
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
