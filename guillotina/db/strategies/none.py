from guillotina import configure
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionStrategy
from guillotina.db.strategies.base import BaseStrategy


@configure.adapter(for_=ITransaction, provides=ITransactionStrategy, name="none")
class TransactionlessStrategy(BaseStrategy):
    """
    Do not handle/detect any conflicts on the database
    """

    async def tpc_begin(self):
        self._transaction._tid = 1


@configure.adapter(for_=ITransaction, provides=ITransactionStrategy, name="tidonly")
class TIDOnlyStrategy(BaseStrategy):
    """
    Still issue a transaction id and never issue explicit transaction
    """

    async def tpc_commit(self):
        await self.retrieve_tid()
