# -*- coding: utf-8 -*-
from plone.server.json.interfaces import IResourceFieldDeserializer
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface
from zope.schema.interfaces import IField
from zope.schema.interfaces import IFromUnicode


@implementer(IResourceFieldDeserializer)
@adapter(IField, Interface, Interface)
class DefaultResourceFieldDeserializer(object):

    def __init__(self, field, context, request):
        self.field = field
        self.context = context
        self.request = request

    def __call__(self, value):
        if not isinstance(value, str) or not isinstance(value, bytes):
            return value
        return IFromUnicode(self.field).fromUnicode(value)
