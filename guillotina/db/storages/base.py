class BaseStorage(object):

    _cache = {}
    _read_only = False

    def __init__(self, read_only=False):
        self._read_only = read_only

    def use_cache(self, value):
        self._cache = value

    def read_only(self):
        return self._read_only
