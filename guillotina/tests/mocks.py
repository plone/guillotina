from guillotina.db.interfaces import IStorage
from zope.interface import implementer


@implementer(IStorage)
class MockStorage:

    _cache = {}
    _read_only = False
    _transaction_strategy = 'merge'

    async def get_annotation(self, trns, oid, id):
        return None


class MockManager:
    _storage = MockStorage()
