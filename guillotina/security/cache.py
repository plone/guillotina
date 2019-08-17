class SecurityMapCacheManager:
    def __init__(self):
        self._cache = {}

    def __contains__(self, key):
        return key in self._cache

    def get(self, key, default=None):
        return self._cache.get(key, default)

    def apply(self, key, security_map):
        security_map._byrow = self._cache[key]["byrow"]
        security_map._bycol = self._cache[key]["bycol"]

    def put(self, key, security_map):
        self._cache[key] = {"byrow": security_map._byrow, "bycol": security_map._bycol}
