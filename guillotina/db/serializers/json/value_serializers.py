from .interfaces import IStorageSerializer
from guillotina import configure
from guillotina.utils import get_dotted_name
from zope.interface import Interface

import base64
import pickle


@configure.adapter(
    for_=Interface, provides=IStorageSerializer, name="$.AnyObjectDict",
)
class AnyObjectSerializer:
    def __init__(self, obj):
        self.obj = obj

    def __call__(self):
        return {
            **{"__class__": get_dotted_name(self.obj)},
            **self.obj.__dict__,
        }


@configure.adapter(for_=Interface, provides=IStorageSerializer, name="builtins.set")
@configure.adapter(for_=Interface, provides=IStorageSerializer, name="builtins.frozenset")
class SetSerializer:
    def __init__(self, obj):
        self.obj = obj

    def __call__(self):
        return {
            "__class__": get_dotted_name(type(self.obj)),
            "__value__": list(self.obj),
        }


@configure.adapter(for_=Interface, provides=IStorageSerializer, name="datetime.datetime")
class DatetimeSerializer:
    def __init__(self, obj):
        self.obj = obj

    def __call__(self):
        return {
            "__class__": get_dotted_name(type(self.obj)),
            "__value__": self.obj.isoformat(),
        }


@configure.adapter(
    for_=Interface, provides=IStorageSerializer, name="zope.interface.declarations.Implements",
)
class ImplementsSerializer:
    def __init__(self, obj):
        self.obj = obj

    def __call__(self):
        return {
            "__class__": "zope.interface.declarations.Implements",
            "__name__": self.obj.__name__,
            "__ifaces__": [i.__identifier__ for i in self.obj.flattened()],
        }


@configure.adapter(
    for_=Interface, provides=IStorageSerializer, name="zope.interface.Provides",
)
class ProvidesSerializer:
    def __init__(self, obj):
        self.obj = obj

    def __call__(self):
        return {
            "__class__": "zope.interface.Provides",
            # "__ifaces__": [i.__identifier__ for i in self.obj.flattened()],
            "__pickle__": base64.b64encode(pickle.dumps(self.obj)).decode(),
        }


@configure.adapter(
    for_=Interface, provides=IStorageSerializer, name="guillotina.security.securitymap.SecurityMap",
)
class SecurityMapSerializer:
    def __init__(self, obj):
        self.obj = obj

    def __call__(self):
        return {
            "__class__": "guillotina.security.securitymap.SecurityMap",
            "__dict__": self.obj.__dict__,
        }
