from zope.interface import Interface


class IRateLimitingStateManager(Interface):
    """
    Keeps the state about service requests rate
    """
    async def increment(self, key):
        """Increments the request counter for the service key
        """
        pass

    async def get_count(self, key):
        """Gets the current request counter for the service key
        """
        pass

    async def expire_after(self, key, ttl):
        """Schedules the counter reset for a key after the specified ttl
        """
        pass

    async def get_remaining_time(self, key):
        """Gets the remaining time until the counter is reset
        """
        pass

    async def get_all_counts(self):
        """Returns the counters for all registered keys
        """
        pass
