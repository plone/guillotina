from guillotina import configure
from guillotina.interfaces import IRateLimitingStateManager
from .utils import Timer
import functools


@configure.utility(provides=IRateLimitingStateManager, name='memory')
class MemoryRateLimitingStateManager:
    def __init__(self):
        self._counts = {}
        self._timers = {}

    async def increment(self, user, key):
        self._counts.setdefault(user, {})
        self._counts[user].setdefault(key, 0)
        self._counts[user][key] += 1

    async def get_count(self, user, key):
        return self._counts.get(user, {}).get(key, 0)

    async def _expire_key(self, user, key):
        if user in self._counts:
            self._counts[user].pop(key, None)

        if user in self._timers:
            self._timers[user].pop(key, None)

    async def expire_after(self, user, key, ttl):
        callback = functools.partial(self._expire_key, user, key)
        self._timers.setdefault(user, {})
        self._timers[user][key] = Timer(ttl, callback)

    async def get_remaining_time(self, user, key):
        if key not in self._timers.get(user, {}):
            return 0
        return self._timers[user][key].remaining
