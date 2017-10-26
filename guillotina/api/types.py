from guillotina import configure
from guillotina.api.service import TraversableService
from guillotina.component import get_multi_adapter
from guillotina.component import get_utilities_for
from guillotina.component import query_utility
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
            self.value = query_utility(IResourceFactory, name=traverse[0])
            if self.value is None:
                raise KeyError(traverse[0])
        return self

    async def __call__(self):
        if not hasattr(self, 'value'):
            self.value = [x[1] for x in get_utilities_for(IResourceFactory)]
        if isinstance(self.value, list):
            result = []
            for x in self.value:
                serializer = get_multi_adapter(
                    (x, self.request),
                    IFactorySerializeToJson)

                result.append(await serializer())
        else:
            serializer = get_multi_adapter(
                (self.value, self.request),
                IFactorySerializeToJson)

            result = await serializer()
        return result
