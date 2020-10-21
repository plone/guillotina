class BaseStrategy:
    def __init__(self, transaction):
        self._storage = transaction._manager._storage
        self._transaction = transaction

    @property
    def writable_transaction(self):
        return not self._transaction.read_only

    async def tpc_begin(self):
        self._transaction._tid = -1  # temporary before committing

    async def tpc_commit(self):
        pass

    async def tpc_vote(self):
        return True

    async def tpc_finish(self):
        pass
