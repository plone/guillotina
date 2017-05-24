from guillotina import configure
from guillotina.db.interfaces import IDBTransactionStrategy
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.strategies.simple import SimpleStrategy

import logging


logger = logging.getLogger('guillotina')


@configure.adapter(
    for_=(IStorage, ITransaction),
    provides=IDBTransactionStrategy, name="novote")
class NoVoteStrategy(SimpleStrategy):
    '''
    Get us a transaction, but we don't care about voting
    '''

    async def tpc_vote(self):
        return True
