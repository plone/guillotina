# -*- coding: utf-8 -*-
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.server.api.service import TraversableService
from zope.component import getMultiAdapter
from zope.interface.interfaces import ComponentLookupError
from plone.dexterity.fti import IDexterityFTI
from zope.component import getUtilitiesFor
from zope.component import queryUtility


class Read(TraversableService):

    def publishTraverse(self, traverse):
        if len(traverse) == 1:
            # we want have the key of the registry
            self.value = queryUtility(IDexterityFTI, name=traverse[0])
        return self

    async def __call__(self):
        if not hasattr(self, 'value'):
            self.value = [x[1] for x in getUtilitiesFor(IDexterityFTI)]
        if isinstance(self.value, list):
            result = []
            for x in self.value:
                serializer = getMultiAdapter(
                    (x, self.request),
                    ISerializeToJson)

                result.append(serializer())
        else:
            serializer = getMultiAdapter(
                (self.value, self.request),
                ISerializeToJson)

            result = serializer()
        return result
