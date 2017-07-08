

class BaseStrategy:
    '''
    Do not attempt to resolve conflicts but detect for them
    '''
    def __init__(self, storage, transaction):
        self._storage = storage
        self._transaction = transaction

    @property
    def writable_transaction(self):
        req = self._transaction.request
        if hasattr(req, '_db_write_enabled'):
            return req._db_write_enabled
        return True

    async def tpc_begin(self):
        pass

    async def tpc_vote(self):
        return True

    async def tpc_finish(self):
        pass
