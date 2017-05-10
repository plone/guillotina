from guillotina.component import getAdapter
from guillotina.db.interfaces import IStorageCache


class BaseStorage(object):

    _cache_strategy = 'dummy'
    _read_only = False
    _transaction_strategy = 'merge'

    def __init__(self, read_only=False, transaction_strategy='merge',
                 cache_strategy='dummy'):
        self._read_only = read_only
        self._transaction_strategy = transaction_strategy
        self._cache = getAdapter(self, IStorageCache, name=cache_strategy)

    def read_only(self):
        return self._read_only
