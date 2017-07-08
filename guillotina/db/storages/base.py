

class BaseStorage(object):

    _cache_strategy = 'dummy'
    _read_only = False
    _transaction_strategy = 'resolve'

    def __init__(self, read_only=False, transaction_strategy='resolve',
                 cache_strategy='dummy'):
        self._read_only = read_only
        self._transaction_strategy = transaction_strategy
        self._cache_strategy = cache_strategy

    def read_only(self):
        return self._read_only
