from guillotina import configure
from guillotina.component import queryAdapter
from guillotina.db.interfaces import IPartition
from guillotina.db.interfaces import IWriter
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.interfaces import ICatalogDataAdapter
from guillotina.interfaces import IResource
from guillotina.utils import get_class_dotted_name

import pickle


@configure.adapter(
    for_=(IBaseObject),
    provides=IWriter)
class Writer(object):

    part = 0
    resource = False

    def __init__(self, obj):
        self._obj = obj

    async def get_json(self):
        return None

    @property
    def of(self):
        return getattr(self._obj, '__of__', None)

    @property
    def type(self):
        return get_class_dotted_name(self._obj)

    @property
    def old_serial(self):
        return getattr(self._obj, '_p_serial', None)

    @property
    def part(self):
        of = self.of
        if of is not None:
            writer = Writer(of)
            return writer.part
        return None

    def serialize(self):
        if self._obj is not None:
            return pickle.dumps(self._obj, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            return None

    @property
    def parent_id(self):
        parent = getattr(self._obj, '__parent__', None)
        if parent is not None:
            return parent._p_oid

    @property
    def id(self):
        return getattr(self._obj, 'id', None)


@configure.adapter(
    for_=(IResource),
    provides=IWriter)
class ResourceWriter(Writer):

    resource = True

    @property
    def part(self):
        if self._obj is not None:
            adapter = queryAdapter(self._obj, IPartition)
            if adapter is not None:
                return adapter()
        return None

    @property
    def type(self):
        if self._obj is not None and hasattr(self._obj, 'type_name'):
            return self._obj.type_name
        else:
            return get_class_dotted_name(self._obj)

    async def get_json(self):
        adapter = queryAdapter(self._obj, ICatalogDataAdapter)
        if adapter is not None:
            return await adapter()
