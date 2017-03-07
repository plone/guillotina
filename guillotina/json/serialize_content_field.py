# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.interfaces import IResourceFieldSerializer
from guillotina.json.serialize_value import json_compatible
from zope.interface import Interface
from guillotina.schema.interfaces import IField
from guillotina.utils import apply_coroutine


@configure.adapter(
    for_=(IField, Interface, Interface),
    provides=IResourceFieldSerializer)
class DefaultFieldSerializer(object):

    def __init__(self, field, context, request):
        self.context = context
        self.request = request
        self.field = field

    async def __call__(self):
        return json_compatible(await self.get_value())

    async def get_value(self, default=None):
        try:
            return await apply_coroutine(
                self.field.get,
                self.context)
        except:  # noqa
            # XXX handle exception?
            return await apply_coroutine(
                getattr,
                self.context,
                self.field.__name__,
                default)
