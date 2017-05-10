from guillotina import configure
from guillotina.db.cache.base import BaseCache
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import IStorageCache


@configure.adapter(for_=IStorage, provides=IStorageCache, name="dummy")
class DummyCache(BaseCache):

    async def get(self, name, default=None):
        return default

    async def get_child(self, container, id):
        pass

    async def set_child(self, container, id, value):
        pass

    async def set(self, ob, value):
        pass

    async def clear(self):
        pass

    async def invalidate(self, ob):
        pass
