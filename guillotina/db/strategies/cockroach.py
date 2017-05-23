from guillotina import configure
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionStrategy
from guillotina.db.strategies.simple import SimpleStrategy
from guillotina.db.strategies.resolve import ResolveStrategy

import logging


logger = logging.getLogger('guillotina')


@configure.adapter(
    for_=(IStorage, ITransaction),
    provides=ITransactionStrategy, name="cockroach")
class CockroachStrategy(SimpleStrategy):
    '''
    Special transaction strategy that works with cockroachdb which:
    - starts trnsaction
    - gets transaction id
    - does *not* do voting
        - default tid matching on storing should be enough with cockroach's
          approach to ACID(which already is restrictive)
    '''

    async def tpc_begin(self):
        await self._storage.start_transaction(self._transaction)
        if self.writable_transaction:
            tid = await self._storage.get_next_tid(self._transaction)
            if tid is not None:
                self._transaction._tid = tid

    async def tpc_vote(self):
        return True


@configure.adapter(
    for_=(IStorage, ITransaction),
    provides=ITransactionStrategy, name="cockroach-txnless")
class CockroachTransactionlessStrategy(ResolveStrategy):
    '''
    Special transaction strategy that works with cockroachdb which:
    - No db transaction
    - Gets transaction id
    - Still does voting
    '''

    async def tpc_begin(self):
        if self.writable_transaction:
            tid = await self._storage.get_next_tid(self._transaction)
            if tid is not None:
                self._transaction._tid = tid
