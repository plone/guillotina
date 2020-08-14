from guillotina.contrib.proto.interfaces import IProtoData
from guillotina import app_settings


@configure.adapter(for_=(IProtoData), provides=IWriter)
class Writer(object):

    resource = False

    def __init__(self, obj):
        self._obj = obj

    @property
    def type(self):
        return self._obj.__plass__.__class__

    async def get_json(self):
        if not app_settings.get("store_json_proto", False) and hasattr(self._obj, '_pbdata'):
            return {}

        return self._obj.MessageToDict()

    @property
    def of(self):
        return getattr(self._obj, "__of__", None)

    @property
    def type(self):
        return get_dotted_name(self._obj)

    @property
    def old_serial(self):
        return getattr(self._obj, "__serial__", None)

    @property
    def part(self):
        return getattr(self._obj, "__partition_id__", 0)

    def serialize(self):
        return self._obj.SerializeToString()

    @property
    def parent_id(self):
        parent = getattr(self._obj, "__parent__", None)
        if parent is not None:
            return parent.__uuid__

    @property
    def id(self):
        return getattr(self._obj, "id", None)
