from .interfaces import IStorageSerializer
from guillotina import configure
from guillotina.component import get_adapter
from guillotina.component import query_adapter
from guillotina.db.interfaces import IWriter
from guillotina.db.serializers.pickle import writer
from guillotina.interfaces import IAnnotationData
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IResource
from guillotina.interfaces.security import PermissionSetting
from guillotina.utils import get_dotted_name
from zope.interface.interface import InterfaceClass

import orjson


def json_default(obj):
    if type(obj) == str:
        return obj
    elif isinstance(obj, complex):
        return [obj.real, obj.imag]
    elif isinstance(obj, type):
        return obj.__module__ + "." + obj.__name__
    elif isinstance(obj, InterfaceClass):
        return [x.__module__ + "." + x.__name__ for x in obj.__iro__]  # noqa
    elif type(obj) == dict:
        return obj
    elif isinstance(obj, PermissionSetting):
        return obj.get_name()

    dotted_name = get_dotted_name(type(obj))
    adapter = query_adapter(obj, IStorageSerializer, name=dotted_name)
    if adapter is None:
        adapter = get_adapter(obj, IStorageSerializer, name="$.AnyObjectDict")
    return adapter()


@configure.adapter(for_=(IResource), provides=IWriter, name="json")
class Writer(writer.ResourceWriter):
    collection = "Objects"

    def serialize(self):
        d = {
            **self._obj.__dict__,
            **{
                "type_name": self._obj.type_name,
                "__class__": get_dotted_name(self._obj),
                "__behaviors__": self._obj.__behaviors__,
                "__providedBy__": self._obj.__providedBy__,
                "__implemented__": self._obj.__implemented__,
            },
        }
        d.pop("__provides__", None)

        return orjson.dumps(
            d, default=json_default, option=orjson.OPT_PASSTHROUGH_DATETIME | orjson.OPT_NON_STR_KEYS,
        )


@configure.adapter(for_=(IAnnotationData), provides=IWriter, name="json")
class AnnotationWriter(writer.Writer):
    collection = "Annotations"

    def serialize(self):
        return orjson.dumps(
            {
                **self._obj.__dict__,
                **{
                    "__class__": get_dotted_name(self._obj),
                    "__providedBy__": self._obj.__providedBy__,
                    "__implemented__": self._obj.__implemented__,
                },
            },
            default=json_default,
            option=orjson.OPT_PASSTHROUGH_DATETIME | orjson.OPT_NON_STR_KEYS,
        )


@configure.adapter(for_=(IDatabase), provides=IWriter, name="json")
class DatabaseWriter(writer.Writer):
    def serialize(self):
        d = orjson.dumps(
            {
                **self._obj.__dict__,
                **{
                    "type_name": self._obj.type_name,
                    "__class__": get_dotted_name(self._obj),
                    "__providedBy__": self._obj.__providedBy__,
                    "__implemented__": self._obj.__implemented__,
                },
            },
            default=json_default,
            option=orjson.OPT_PASSTHROUGH_DATETIME | orjson.OPT_NON_STR_KEYS,
        )
        return d
