from guillotina.contrib.proto.annotation import ProtoData
from guillotina.contrib.proto.interfaces import IProtoData
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import IContentBehavior
from guillotina.schema.utils import get_default_from_schema
from guillotina.contrib.proto.reader import reader as proto_reader
from typing import Tuple
from zope.interface import implementer


_default = object()


@implementer(IAsyncBehavior)
class ProtoBehavior:
    """A factory that knows how to store data in a separate object."""

    auto_serialize = True

    __local__properties__: Tuple[str, ...] = ()  # bbb

    # each annotation is stored
    __annotations_data_key__ = "proto"

    def __init__(self, context):
        self.__dict__["schema"] = [x for x in self.__implemented__][0]
        self.__annotations_data_key__ = self.__dict__["schema"].__plass__
        self.__dict__["data"] = None
        self.__dict__["context"] = context

        # see if annotations are preloaded...
        annotations_container = IAnnotations(self.__dict__["context"])
        data = annotations_container.get(self.__annotations_data_key__, _default, reader=proto_reader)
        if data is not _default:
            self.__dict__["data"] = data

    async def load(self, create=False):
        annotations_container = IAnnotations(self.__dict__["context"])
        data = annotations_container.get(self.__annotations_data_key__, _default, reader=proto_reader)
        if data is not _default:
            # data is already preloaded, we do not need to get from db again...
            self.__dict__["data"] = data
            return

        annotations = await annotations_container.async_get(self.__annotations_data_key__, reader=proto_reader)
        if annotations is None:
            annotations = ProtoData()
            annotations.__set_plass__(self.__dict__["schema"].__plass__)
            if create:
                await annotations_container.async_set(self.__annotations_data_key__, annotations)
        self.__dict__["data"] = annotations

    def __getattr__(self, name):
        if name not in self.__dict__["schema"]:
            return super(ProtoBehavior, self).__getattr__(name)
        return self.__dict__["data"].__getattr__(name)

    def __setattr__(self, name, value):
        if (
            name not in self.__dict__["schema"]
            or name.startswith("__")
            or name in self.__local__properties__
            or name in vars(type(self))
        ):
            super(ProtoBehavior, self).__setattr__(name, value)
        else:
            self.__dict__["data"].__setattr__(name, value)
            self.__dict__["data"].register()

    def register(self):
        if IProtoData.providedBy(self.__dict__["data"]):
            self.__dict__["data"].register()
