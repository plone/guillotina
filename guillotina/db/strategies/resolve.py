from guillotina import configure
from guillotina.db.interfaces import IDBTransactionStrategy
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.strategies.simple import SimpleStrategy

import logging


logger = logging.getLogger('guillotina')


@configure.adapter(
    for_=(IStorage, ITransaction),
    provides=IDBTransactionStrategy, name="resolve")
class ResolveStrategy(SimpleStrategy):
    '''
    If simultaneous transactions are not editing the same objects, let it go
    '''

    async def tpc_vote(self):
        if not self.writable_transaction:
            return True
        current_tid = await self._storage.get_current_tid(self._transaction)
        if current_tid > self._transaction._tid:
            # potential conflict error, get changes
            # Check if there is any commit bigger than the one we already have
            conflicts = await self._storage.get_conflicts(self._transaction)
            for conflict in conflicts:
                # both writing to same object...
                if conflict['zoid'] in self._transaction.modified:
                    return False
            if len(conflicts) > 0:
                logger.info('Resolved conflict between transaction ids: {}, {}'.format(
                    self._transaction._tid, current_tid
                ))

        return True
