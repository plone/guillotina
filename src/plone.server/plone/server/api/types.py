# -*- coding: utf-8 -*-
from plone.server.api.service import TraversableService
from plone.server import configure
from plone.server.interfaces import IResourceFactory
from plone.server.interfaces import ISite
from plone.server.json.interfaces import IFactorySerializeToJson
from zope.component import getMultiAdapter
from zope.component import getUtilitiesFor
from zope.component import queryUtility


@configure.service(context=ISite, method='GET', permission='plone.AccessContent',
                   name='@types')
class Read(TraversableService):

    def publishTraverse(self, traverse):
        if len(traverse) == 1:
            # we want have the key of the registry
            self.value = queryUtility(IResourceFactory, name=traverse[0])
        return self

    async def __call__(self):
        if not hasattr(self, 'value'):
            self.value = [x[1] for x in getUtilitiesFor(IResourceFactory)]
        if isinstance(self.value, list):
            result = []
            for x in self.value:
                serializer = getMultiAdapter(
                    (x, self.request),
                    IFactorySerializeToJson)

                result.append(serializer())
        else:
            serializer = getMultiAdapter(
                (self.value, self.request),
                IFactorySerializeToJson)

            result = serializer()
        return result
