from .interfaces import IStorageDeserializer
from dateutil.parser import parse
from guillotina import configure
from guillotina.interfaces.security import PermissionSetting
from guillotina.security.securitymap import SecurityMap
from guillotina.utils import resolve_dotted_name
from zope.interface import Interface
from zope.interface.declarations import Implements

import base64
import pickle


@configure.adapter(
    for_=Interface, provides=IStorageDeserializer, name="$.AnyObjectDict",
)
class AnyObjectDeserializer:
    def __init__(self, data):
        self.data = data

    def __call__(self):
        klass = self.data.pop("__class__")
        type_class = resolve_dotted_name(klass)
        obj = type_class.__new__(type_class)
        obj.__dict__ = self.data
        return obj


@configure.adapter(for_=Interface, provides=IStorageDeserializer, name="builtins.set")
@configure.adapter(for_=Interface, provides=IStorageDeserializer, name="builtins.frozenset")
class SetDeseializer:
    def __init__(self, data):
        self.data = data

    def __call__(self):
        data = self.data
        if data["__class__"] == "builtins.set":
            return set(data["__value__"])
        else:
            return frozenset(data["__value__"])


@configure.adapter(for_=Interface, provides=IStorageDeserializer, name="datetime.datetime")
class DatetimeDeserializer:
    def __init__(self, data):
        self.data = data

    def __call__(self):
        return parse(self.data["__value__"])


@configure.adapter(
    for_=Interface, provides=IStorageDeserializer, name="zope.interface.declarations.Implements",
)
class ImplementsDeseializer:
    def __init__(self, data):
        self.data = data

    def __call__(self):
        data = self.data
        obj = Implements()
        obj.__bases__ = [resolve_dotted_name(iface) for iface in data["__ifaces__"]]
        obj.__name__ = data["__name__"]
        return obj


@configure.adapter(
    for_=Interface, provides=IStorageDeserializer, name="zope.interface.Provides",
)
class ProvidesDeserializer:
    def __init__(self, data):
        self.data = data

    def __call__(self):
        # from zope.interface import Provides  # type: ignore
        # obj = Provides(*[resolve_dotted_name(iface) for iface in self.data["__ifaces__"]])
        # return obj
        return pickle.loads(base64.b64decode(self.data["__pickle__"]))


@configure.adapter(
    for_=Interface, provides=IStorageDeserializer, name="guillotina.security.securitymap.SecurityMap",
)
class SecurityMapDeserializer:
    def __init__(self, data):
        self.data = data

    def __call__(self):
        sec_map = SecurityMap.__new__(SecurityMap)
        sec_map.__dict__.update(
            {
                # byrow
                k: {
                    # Role
                    k2: {
                        # Principal
                        k3: PermissionSetting(v3)
                        for k3, v3 in v2.items()
                    }
                    for k2, v2 in v.items()
                }
                for k, v in self.data["__dict__"].items()
            }
        )
        return sec_map
