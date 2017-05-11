

class BaseCache:

    def __init__(self, storage):
        self._storage = storage

    async def get(self, oid=None, container=None, id=None, variant=None):
        '''
        Use params to build cache key
        MUST return dictionary-like object with these keys:
            - state: the pickle value
            - zoid: object unique id in the database
            - tid: transaction id for ob
            - id
        '''
        raise NotImplemented()

    async def set(self, value, oid=None, container=None, id=None, variant=None):
        '''
        Use params to build cache key
        '''
        raise NotImplemented()

    async def clear(self):
        raise NotImplemented()

    async def invalidate(self, ob):
        raise NotImplemented()
