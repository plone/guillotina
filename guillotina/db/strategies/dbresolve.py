from guillotina import configure
from guillotina.db.interfaces import IDBTransactionStrategy
from guillotina.db.interfaces import ITransaction
from guillotina.db.strategies.simple import SimpleStrategy

import logging


logger = logging.getLogger('guillotina')


@configure.adapter(
    for_=ITransaction, provides=IDBTransactionStrategy, name="dbresolve")
class DBResolveStrategy(SimpleStrategy):
    '''
    Get us a transaction, but we don't care about voting
    '''

    async def tpc_vote(self):
        return True


@configure.adapter(
    for_=ITransaction, provides=IDBTransactionStrategy, name="dbresolve_readcommitted")
class DBResolveReadCommittedStrategy(DBResolveStrategy):
    '''
    Delay starting transaction to the commit phase so reads will be inconsistent.
    '''

    async def tpc_begin(self):
        pass

    async def tpc_commit(self):
        if self._transaction._tid in (-1, 1, None):
            await self.retrieve_tid()
        await self._storage.start_transaction(self._transaction)
