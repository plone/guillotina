# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.api.service import TraversableService
from guillotina.interfaces import IFactorySerializeToJson
from guillotina.interfaces import IResourceFactory
from guillotina.interfaces import ISite
from zope.component import getMultiAdapter
from zope.component import getUtilitiesFor
from zope.component import queryUtility


@configure.service(context=ISite, method='GET', permission='guillotina.AccessContent',
                   name='@types')
class Read(TraversableService):

    async def publish_traverse(self, traverse):
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

                result.append(await serializer())
        else:
            serializer = getMultiAdapter(
                (self.value, self.request),
                IFactorySerializeToJson)

            result = await serializer()
        return result
