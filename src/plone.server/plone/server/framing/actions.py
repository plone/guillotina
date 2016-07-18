from zope.component import adapter
from zope.interface import implementer
from plone.server.renderers import IFrameFormatsJson
from plone.server.interfaces import IRequest


@adapter(IRequest)
@implementer(IFrameFormatsJson)
class Framing(object):

    def __init__(self, request):
        self.request = request

    def __call__(self, json_value):
        json_value['actions'] = []
        return json_value
