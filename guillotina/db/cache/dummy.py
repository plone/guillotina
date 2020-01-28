from guillotina import configure
from guillotina.db.cache.base import BaseCache
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionCache
from typing import Any
from typing import Dict
from typing import List


@configure.adapter(for_=ITransaction, provides=ITransactionCache, name="dummy")
class DummyCache(BaseCache):
    async def get(self, **kwargs):
        return None

    async def set(
        self, value, keyset: List[Dict[str, Any]] = None, oid=None, container=None, id=None, variant=None
    ):
        ...

    async def clear(self):
        ...

    async def invalidate(self, ob):
        ...

    async def delete(self, key):
        ...

    async def delete_all(self, keys):
        ...
