from guillotina import configure
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.renderers import IFrameFormatsJson
from zope.component import getMultiAdapter
from zope.component import queryUtility
from zope.component.interfaces import IFactory


@configure.adapter(for_=IRequest, provides=IFrameFormatsJson, name="schema")
class Framing(object):

    def __init__(self, request):
        self.request = request

    async def __call__(self, json_value):
        if self.request.resource:
            fti = queryUtility(
                IFactory, name=self.request.resource.portal_type)
            schema_summary = getMultiAdapter(
                (fti, self.request), IResourceSerializeToJson)
            json_value['schema'] = await schema_summary()
        return json_value
