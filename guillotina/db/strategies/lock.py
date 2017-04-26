from guillotina import configure
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionStrategy


@configure.adapter(
    for_=(IStorage, ITransaction),
    provides=ITransactionStrategy, name="lock")
class LockStrategy:
    '''
    XXX not implemented

    Will lock rows for writing to
    '''
    def __init__(self, storage, transaction):
        self._storage = storage
        self._transaction = transaction

    async def tpc_begin(self):
        self._transaction._tid = 1

    async def tpc_vote(self):
        return True

    async def tpc_finish(self):
        pass
