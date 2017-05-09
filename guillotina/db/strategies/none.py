from guillotina import configure
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionStrategy
from guillotina.db.strategies.base import BaseStrategy


@configure.adapter(
    for_=(IStorage, ITransaction),
    provides=ITransactionStrategy, name="none")
class TransactionlessStrategy(BaseStrategy):
    """
    Do not handle/detect any conflicts on the database
    """
    def __init__(self, storage, transaction):
        self._storage = storage
        self._transaction = transaction

    async def tpc_begin(self):
        self._transaction._tid = 1

    async def tpc_vote(self):
        return True

    async def tpc_finish(self):
        pass
