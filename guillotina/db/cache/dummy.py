from typing import Any, Dict, List

from guillotina import configure
from guillotina.db.cache.base import BaseCache
from guillotina.db.interfaces import ITransaction, ITransactionCache


@configure.adapter(for_=ITransaction, provides=ITransactionCache, name="dummy")
class DummyCache(BaseCache):
    async def get(self, **kwargs):
        return None

    async def set(
        self, value, keyset: List[Dict[str, Any]] = None, oid=None, container=None, id=None, variant=None
    ):
        pass

    async def clear(self):
        pass

    async def invalidate(self, ob):
        pass

    async def delete(self, key):
        pass

    async def delete_all(self, keys):
        pass
