from guillotina import configure
from guillotina.interfaces import IRequest
from guillotina.renderers import IFrameFormatsJson


@configure.adapter(for_=IRequest, provides=IFrameFormatsJson, name="actions")
class Framing(object):

    def __init__(self, request):
        self.request = request

    async def __call__(self, json_value):
        json_value['actions'] = []
        return json_value
