

class MockStorage:

    _cache = {}

    async def get_annotation(self, trns, oid, id):
        return None


class MockManager:
    _storage = MockStorage()
