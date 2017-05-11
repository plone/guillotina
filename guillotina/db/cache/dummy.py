from guillotina import configure
from guillotina.db.cache.base import BaseCache
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import IStorageCache


@configure.adapter(for_=IStorage, provides=IStorageCache, name="dummy")
class DummyCache(BaseCache):

    async def get(self, **kwargs):
        return None

    async def set(self, value, **kwargs):
        pass

    async def clear(self):
        pass

    async def invalidate(self, ob):
        pass
