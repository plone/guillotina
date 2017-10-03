# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.component import ComponentLookupError
from guillotina.component import getMultiAdapter
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IJSONToValue
from guillotina.interfaces import IResourceFieldDeserializer
from guillotina.json.deserialize_value import schema_compatible
from guillotina.schema.interfaces import IField
from guillotina.utils import apply_coroutine
from zope.interface import Interface

import logging


logger = logging.getLogger('guillotina')


@configure.adapter(
    for_=(IField, Interface, Interface),
    provides=IResourceFieldDeserializer)
class DefaultResourceFieldDeserializer(object):

    def __init__(self, field, context, request):
        self.field = field
        self.context = context
        self.request = request

    def __call__(self, value):
        schema = self.field
        value = schema_compatible(value, schema)
        self.field.validate(value)
        return value


@configure.adapter(
    for_=(ICloudFileField, Interface, Interface),
    provides=IResourceFieldDeserializer)
class CloudFileResourceFieldDeserializer(DefaultResourceFieldDeserializer):
    '''
    Cloud file value adapters are callable adapters so we can do async
    methods on them
    '''

    async def __call__(self, value):
        try:
            # cloud files are callable adapters...
            converter = getMultiAdapter((value, self.field), IJSONToValue)
            if callable(converter):
                val = await apply_coroutine(converter, self.context, self.request)
            else:
                val = converter
            self.field.validate(val)
            return val
        except ComponentLookupError:
            logger.error((u'Deserializer not found for field type '
                          u'"{0:s}" with value "{1:s}" and it was '
                          u'deserialized to None.').format(
                repr(self.field), value))
            return None
