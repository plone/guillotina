from zope.component import adapter
from zope.component import queryUtility
from zope.component import getMultiAdapter
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.dexterity.interfaces import IDexterityFTI
from zope.interface import implementer
from plone.server.renderers import IFrameFormatsJson
from plone.server.interfaces import IRequest


@adapter(IRequest)
@implementer(IFrameFormatsJson)
class Framing(object):

    def __init__(self, request):
        self.request = request

    def __call__(self, json_value):
        if self.request.resource:
            fti = queryUtility(
                IDexterityFTI, name=self.request.resource.portal_type)
            schema_summary = getMultiAdapter(
                (fti, self.request), ISerializeToJson)()
            json_value['schema'] = schema_summary
        return json_value
