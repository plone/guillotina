from plone.server.api.service import TraversableService
from zope.component import getMultiAdapter
from plone.jsonserializer.interfaces import ISerializeToJson


class Read(TraversableService):

    def traverse_to(self, traverse):
        if len(traverse) == 1:
            # we want have the key of the registry
            serializer = getMultiAdapter(
                (self.request.site_settings[traverse], self.request),
                ISerializeToJson)
            return serializer()
        else:
            return None


class Write(TraversableService):
    pass
