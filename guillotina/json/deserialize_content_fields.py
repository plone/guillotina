# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.interfaces import IResourceFieldDeserializer
from guillotina.json.deserialize_value import schema_compatible
from guillotina.schema.interfaces import IField
from zope.interface import Interface


@configure.adapter(
    for_=(IField, Interface, Interface),
    provides=IResourceFieldDeserializer)
class DefaultResourceFieldDeserializer(object):

    def __init__(self, field, context, request):
        self.field = field
        self.context = context
        self.request = request

    def __call__(self, value):
        # if not isinstance(value, str) and not isinstance(value, bytes):
        #     return value
        schema = self.field
        value = schema_compatible(value, schema)
        self.field.validate(value)
        return value
