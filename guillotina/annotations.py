from collections import UserDict
from guillotina import configure
from guillotina.db.orm.base import BaseObject
from guillotina.db.reader import reader
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IResource


class AnnotationData(BaseObject, UserDict):
    """
    store data on basic dictionary object but also inherit from base object
    """


@configure.adapter(
    for_=IResource,
    provides=IAnnotations)
class AnnotationsAdapter(object):
    """Store annotations on an object
    """

    def __init__(self, obj):
        self.obj = obj

    async def get(self, key, default=None):
        annotations = self.obj.__annotations__
        element = annotations.get(key, default)
        if element is None:
            # Get from DB
            obj = await self.obj._p_jar.get_annotation(self.obj, key)
            if obj:
                annotations[key] = obj
        return annotations[key]

    async def __getitem__(self, key):
        return await self.get(key)

    async def keys(self):
        return await self.obj._p_jar.get_annotation_keys(self.obj._p_oid)

    async def __setitem__(self, key, value):
        await self.set(key, value)

    async def set(self, key, value):
        if not isinstance(value, BaseObject):
            raise KeyError('Not a valid object as annotation')
        annotations = self.obj.__annotations__
        value.id = key  # make sure id is set...
        annotations[key] = value
        value.__of__ = self.obj._p_oid
        value.__name__ = key
        # we register the value
        value._p_jar = self.obj._p_jar
        value._p_jar.register(value)

    async def __delitem__(self, key):
        raise NotImplemented()
