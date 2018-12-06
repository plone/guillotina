from guillotina import app_settings
from guillotina.component import get_utility
from guillotina.interfaces import IRateLimitingStateManager

import asyncio
import time


class Timer:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._start_time = None
        self.finished = False
        self._task = asyncio.ensure_future(self._job())

    @property
    def remaining(self):
        if not self.start_time:
            return self._timeout
        return max((time.time() - self._start_time) - self._timeout, 0)

    async def _job(self):
        self._start_time = time.time()
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self):
        self._task.cancel()
        self.finished = True


def get_rate_limit_state_manager():
    """Returns memory persistent_manager by default
    """
    utility = get_utility(
        IRateLimitingStateManager,
        name=app_settings.get('rate_limiter', {}).get('state_manager', 'memory'),
    )
    return utility
