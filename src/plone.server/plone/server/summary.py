# -*- coding: utf-8 -*-
# from plone.app.contentlisting.interfaces import IContentListingObject
from plone.server.browser import get_physical_path
from plone.jsonserializer.interfaces import ISerializeToJsonSummary
from plone.jsonserializer.serializer.converters import json_compatible
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


@implementer(ISerializeToJsonSummary)
@adapter(Interface, Interface)
class DefaultJSONSummarySerializer(object):
    """Default ISerializeToJsonSummary adapter.

    Requires context to be adaptable to IContentListingObject, which is
    the case for all content objects providing IContentish.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        # obj = IContentListingObject(self.context)
        summary = json_compatible({
            '@id': '/'.join(get_physical_path(self.context)),
            '@type': self.context.portal_type,
            'title': self.context.title,
            'description': self.context.description
        })
        return summary
