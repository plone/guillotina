from guillotina import configure
from guillotina.db.interfaces import ITransactionStrategy
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import ITransaction


@configure.adapter(
    for_=(IStorage, ITransaction),
    provides=ITransactionStrategy, name="simple")
class SimpleStrategy:
    '''
    Do not attempt to resolve conflicts but detect for them
    '''
    def __init__(self, storage, transaction):
        self._storage = storage
        self._transaction = transaction

    async def tpc_begin(self):
        await self._storage.start_transaction(self._transaction)
        tid = await self._storage.get_next_tid(self._transaction)
        if tid is not None:
            self._transaction._tid = tid

    async def tpc_vote(self):
        current_tid = await self._storage.get_current_tid(self._transaction)
        if current_tid > self._transaction._tid:
            return False

        return True

    async def tpc_finish(self):
        await self._storage.commit(self._transaction)
