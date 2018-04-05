from guillotina.component import get_utility
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase


def change_transaction_strategy(strategy='none'):
    root = get_utility(IApplication, name='root')
    for _id, db in root:
        if IDatabase.providedBy(db):
            db._storage._transaction_strategy = strategy
