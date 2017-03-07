from guillotina.db.orm.base import BaseObject
from collections import UserDict
from zope.interface import implementer
from guillotina import configure
from guillotina.interfaces import IResource
from guillotina.db.orm.interfaces import IAnnotations


class Annotations(BaseObject, UserDict):
    """External object that holds a BaseObject"""

    def __init__(self, context):
        self.__belongs = context


@configure.adapter(
    for_=IResource,
    provides=IAnnotations)
class AnnotationsAdapter(object):
    """Store annotations on an object

    Store annotations in the `__annotations__` attribute on a
    `IAttributeAnnotatable` object.
    """

    def __init__(self, obj, context=None):
        self.obj = obj

    def get(self, key, default=None):
        """See zope.annotation.interfaces.IAnnotations"""
        annotations = getattr(self.obj, '__annotations__', None)
        if not annotations:
            return default

        return annotations.get(key, default)

    def __getitem__(self, key):
        annotations = getattr(self.obj, '__annotations__', None)
        if annotations is None:
            raise KeyError(key)

        return annotations[key]

    def keys(self):
        annotations = getattr(self.obj, '__annotations__', None)
        if annotations is None:
            return []

        return annotations.keys()

    def __iter__(self):
        annotations = getattr(self.obj, '__annotations__', None)
        if annotations is None:
            return iter([])

        return iter(annotations)

    def __len__(self):
        annotations = getattr(self.obj, '__annotations__', None)
        if annotations is None:
            return 0

        return len(annotations)

    def __setitem__(self, key, value):
        """See zope.annotation.interfaces.IAnnotations"""
        try:
            annotations = self.obj.__annotations__
        except AttributeError:
            annotations = self.obj.__annotations__ = _STORAGE()

        annotations[key] = value

    def __delitem__(self, key):
        """See zope.app.interfaces.annotation.IAnnotations"""
        try:
            annotation = self.obj.__annotations__
        except AttributeError:
            raise KeyError(key)

        del annotation[key]
