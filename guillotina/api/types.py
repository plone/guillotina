# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.api.service import TraversableService
from guillotina.component import getMultiAdapter
from guillotina.component import getUtilitiesFor
from guillotina.component import queryUtility
from guillotina.interfaces import IContainer
from guillotina.interfaces import IFactorySerializeToJson
from guillotina.interfaces import IResourceFactory


@configure.service(
    context=IContainer, method='GET',
    permission='guillotina.AccessContent', name='@types',
    summary='Read information on available types',
    responses={
        "200": {
            "description": "Result results on types",
            "schema": {
                "properties": {}
            }
        }
    })
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
