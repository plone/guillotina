import pickle

from guillotina import configure
from guillotina._settings import app_settings
from guillotina.catalog.catalog import DefaultCatalogDataAdapter
from guillotina.component import query_adapter
from guillotina.db.interfaces import IJSONDBSerializer
from guillotina.db.interfaces import IWriter
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.interfaces import IContainer
from guillotina.interfaces import IResource
from guillotina.utils import get_dotted_name


@configure.adapter(
    for_=IResource,
    provides=IJSONDBSerializer)
class DefaultJSONDBSerializer(DefaultCatalogDataAdapter):
    '''
    Default serializer just serializer catalog data
    '''

    def get_container_id(self):
        ob = self.content
        while getattr(ob, '__parent__', None) and not IContainer.providedBy(ob):
            ob = ob.__parent__
        if IContainer.providedBy(ob):
            return ob.__name__

    async def __call__(self):
        data = await super().__call__()
        data['container_id'] = self.get_container_id()
        return data


@configure.adapter(
    for_=(IBaseObject),
    provides=IWriter)
class Writer(object):

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
        return get_dotted_name(self._obj)

    @property
    def old_serial(self):
        return getattr(self._obj, '_p_serial', None)

    @property
    def part(self):
        return getattr(self._obj, '__partition_id__', 0)

    def serialize(self):
        return pickle.dumps(self._obj, protocol=pickle.HIGHEST_PROTOCOL)

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
    def type(self):
        if hasattr(self._obj, 'type_name'):
            return self._obj.type_name
        else:
            return get_dotted_name(self._obj)

    async def get_json(self):
        if not app_settings.get('store_json', False):
            return {}
        adapter = query_adapter(self._obj, IJSONDBSerializer)
        if adapter is not None:
            return await adapter()
