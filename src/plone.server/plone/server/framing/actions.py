from plone.server.interfaces import IRequest
from plone.server.renderers import IFrameFormatsJson
from zope.component import adapter
from zope.interface import implementer


@adapter(IRequest)
@implementer(IFrameFormatsJson)
class Framing(object):

    def __init__(self, request):
        self.request = request

    def __call__(self, json_value):
        json_value['actions'] = []
        return json_value
