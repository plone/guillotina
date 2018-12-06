from guillotina import configure
from guillotina.interfaces import IRateLimitingStateManager
from .utils import Timer
import functools


@configure.utility(provides=IRateLimitingStateManager, name='memory')
class MemoryRateLimitingStateManager:
    def __init__(self):
        self._counts = {}
        self._timers = {}

    async def increment(self, key):
        self._counts.setdefault(key, 0)
        self._counts[key] += 1

    async def get_count(self, key):
        return self._count.get(key, 0)

    async def _expire_key(self, key):
        self._counts.pop(key, None)
        self._timers.pop(key, None)

    async def expire_after(self, key, ttl):
        callback = functools.partial(self._expire_key, key)
        self._timers[key] = Timer(ttl, callback)

    async def get_remaining_time(self, key):
        if key not in self._timers:
            return 0
        return self._timers[key].remaining

    async def get_all_counts(self):
        return {key: count for key, count in self._counts.items() if count > 0}
