# -*- coding: utf-8 -*-
from plone.server import configure
from plone.server.interfaces import IResourceFieldSerializer
from plone.server.json.serialize_value import json_compatible
from zope.interface import Interface
from zope.schema.interfaces import IField


@configure.adapter(
    for_=(IField, Interface, Interface),
    provides=IResourceFieldSerializer)
class DefaultFieldSerializer(object):

    def __init__(self, field, context, request):
        self.context = context
        self.request = request
        self.field = field

    def __call__(self):
        return json_compatible(self.get_value())

    def get_value(self, default=None):
        try:
            return self.field.get(self.context)
        except:
            return getattr(self.context,
                           self.field.__name__,
                           default)
