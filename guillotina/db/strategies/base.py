

class BaseStrategy:
    def __init__(self, transaction):
        self._storage = transaction._manager._storage
        self._transaction = transaction

    @property
    def writable_transaction(self):
        req = self._transaction.request
        if hasattr(req, '_db_write_enabled'):
            return req._db_write_enabled
        return True

    async def tpc_begin(self):
        self._transaction._tid = -1  # temporary before committing

    async def tpc_commit(self):
        pass

    async def tpc_vote(self):
        return True

    async def tpc_finish(self):
        pass

    async def retrieve_tid(self):
        if self.writable_transaction:
            tid = await self._storage.get_next_tid(self._transaction)
            if tid is not None:
                self._transaction._tid = tid
