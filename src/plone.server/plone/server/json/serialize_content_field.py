# -*- coding: utf-8 -*-
# from plone.namedfile.interfaces import INamedField
# from plone.namedfile.interfaces import INamedFileField
# from plone.namedfile.interfaces import INamedImageField
from plone.server.interfaces import IResource
from plone.server.json.interfaces import IResourceFieldSerializer
from plone.server.json.serialize_value import json_compatible
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface
from zope.schema.interfaces import IField


@adapter(IField, Interface, Interface)
@implementer(IResourceFieldSerializer)
class DefaultFieldSerializer(object):

    def __init__(self, field, context, request):
        self.context = context
        self.request = request
        self.field = field

    def __call__(self):
        return json_compatible(self.get_value())

    def get_value(self, default=None):
        return getattr(self.context,
                       self.field.__name__,
                       default)
