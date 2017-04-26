class BaseStorage(object):

    _cache = {}
    _read_only = False
    _transaction_strategy = 'merge'

    def __init__(self, read_only=False, transaction_strategy='merge'):
        self._read_only = read_only
        self._transaction_strategy = transaction_strategy

    def use_cache(self, value):
        self._cache = value

    def read_only(self):
        return self._read_only
