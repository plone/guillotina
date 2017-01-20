from plone.server.interfaces import IRequest
from plone.server.interfaces import IResourceSerializeToJson
from plone.server.renderers import IFrameFormatsJson
from zope.component import adapter
from zope.component import getMultiAdapter
from zope.component import queryUtility
from zope.component.interfaces import IFactory
from zope.interface import implementer


@adapter(IRequest)
@implementer(IFrameFormatsJson)
class Framing(object):

    def __init__(self, request):
        self.request = request

    def __call__(self, json_value):
        if self.request.resource:
            fti = queryUtility(
                IFactory, name=self.request.resource.portal_type)
            schema_summary = getMultiAdapter(
                (fti, self.request), IResourceSerializeToJson)()
            json_value['schema'] = schema_summary
        return json_value
