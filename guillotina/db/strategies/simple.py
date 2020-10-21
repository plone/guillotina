from guillotina import configure
from guillotina import glogging
from guillotina.db.interfaces import IDBTransactionStrategy
from guillotina.db.interfaces import ITransaction
from guillotina.db.strategies.base import BaseStrategy


logger = glogging.getLogger("guillotina")


@configure.adapter(for_=ITransaction, provides=IDBTransactionStrategy, name="simple")
class SimpleStrategy(BaseStrategy):
    async def tpc_begin(self):
        await self.retrieve_tid()
        if self._transaction._db_txn is None:
            await self._storage.start_transaction(self._transaction)

    async def tpc_finish(self):
        # do actual db commit
        if self.writable_transaction:
            await self._storage.commit(self._transaction)
