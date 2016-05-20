from plone.server.api.service import TraversableService
from zope.component import getMultiAdapter
from plone.jsonserializer.interfaces import ISerializeToJson
from zope.interface.interfaces import ComponentLookupError


class Read(TraversableService):

    def publishTraverse(self, traverse):
        if len(traverse) == 1:
            # we want have the key of the registry
            self.value = self.plone_registry[traverse[0]]
        else:
            self.value = None
        return self

    async def __call__(self):
        try:
            serializer = getMultiAdapter(
                (self.value, self.request),
                ISerializeToJson)
            return serializer()
        except ComponentLookupError:
            return self.value


class Write(TraversableService):
    pass
