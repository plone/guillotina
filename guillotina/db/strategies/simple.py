from guillotina import configure
from guillotina import glogging
from guillotina.db.interfaces import IDBTransactionStrategy
from guillotina.db.interfaces import ITransaction
from guillotina.db.strategies.base import BaseStrategy


logger = glogging.getLogger("guillotina")


@configure.adapter(for_=ITransaction, provides=IDBTransactionStrategy, name="simple")
class SimpleStrategy(BaseStrategy):
    """
    Do not attempt to resolve conflicts but detect for them
    """

    async def tpc_begin(self):
        await self.retrieve_tid()
        if self._transaction._db_txn is None:
            await self._storage.start_transaction(self._transaction)

    async def tpc_vote(self):
        if not self.writable_transaction:
            return True

        current_tid = await self._storage.get_current_tid(self._transaction)
        if current_tid > self._transaction._tid:
            logger.warn(
                f"Could not resolve conflicts in TID: {self._transaction._tid}\n"
                f"Conflicted TID: {current_tid}"
            )
            return False

        return True

    async def tpc_finish(self):
        # do actual db commit
        if self.writable_transaction:
            await self._storage.commit(self._transaction)
