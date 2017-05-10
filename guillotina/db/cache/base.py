

class BaseCache:

    def __init__(self, storage):
        self._storage = storage

    async def get(self, name, default=None):
        '''
        MUST return dictionary-like object with these keys:
            - state: the pickle value
            - zoid: object unique id in the database
            - tid: transaction id for ob
            - id
        '''
        raise NotImplemented()

    async def get_child(self, container, id):
        raise NotImplemented()

    async def set_child(self, container, id, value):
        raise NotImplemented()

    async def set(self, ob, value):
        raise NotImplemented()

    async def clear(self):
        raise NotImplemented()

    async def invalidate(self, ob):
        raise NotImplemented()
