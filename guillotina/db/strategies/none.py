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

    async def tpc_begin(self):
        self._transaction._tid = 1


@configure.adapter(
    for_=(IStorage, ITransaction),
    provides=ITransactionStrategy, name="tidonly")
class TIDOnlyStrategy(BaseStrategy):
    """
    Still issue a transaction id but not a real transaction
    """

    async def tpc_begin(self):
        if self.writable_transaction:
            tid = await self._storage.get_next_tid(self._transaction)
            if tid is not None:
                self._transaction._tid = tid
