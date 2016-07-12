# -*- coding: utf-8 -*-
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.server.api.service import TraversableService
from zope.component import getMultiAdapter
from zope.interface.interfaces import ComponentLookupError
from plone.registry.interfaces import IRegistry


class Read(TraversableService):

    def publishTraverse(self, traverse):
        if len(traverse) == 1:
            # we want have the key of the registry
            self.value = [self.request.site_settings[traverse[0]]]
        else:
            self.value = None
        return self

    async def __call__(self):
        if not hasattr(self, 'value'):
            self.value = self.request.site_settings
        if IRegistry.providedBy(self.value):
            result = {}
            for x in self.value.records:
                try:
                    serializer = getMultiAdapter(
                        (self.value[x], self.request),
                        ISerializeToJson)
                    value = serializer()
                except ComponentLookupError:
                    value = self.value[x]
                result[x] = value
        else:
            try:
                serializer = getMultiAdapter(
                    (self.value, self.request),
                    ISerializeToJson)

                result = serializer()
            except ComponentLookupError:
                result = self.value
        return result


class Write(TraversableService):
    pass
