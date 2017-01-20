from plone.server.interfaces import IRequest
from plone.server.renderers import IFrameFormatsJson
from plone.server import configure


@configure.adapter(for_=IRequest, provides=IFrameFormatsJson, name="actions")
class Framing(object):

    def __init__(self, request):
        self.request = request

    def __call__(self, json_value):
        json_value['actions'] = []
        return json_value
