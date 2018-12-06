from zope.interface import Interface


class IRateLimit(Interface):
    pass


class IRateLimitingStateManager(Interface):
    """
    Keeps the state about service requests counts on a per-user basis
    """
    async def increment(self, user, key):
        """Increments the request counter for the service key
        """
        pass

    async def get_count(self, user, key):
        """Gets the current request counter for the service key
        """
        pass

    async def expire_after(self, user, key, ttl):
        """Schedules the counter reset for a key after the specified ttl
        """
        pass

    async def get_remaining_time(self, user, key):
        """Gets the remaining time until the counter is reset
        """
        pass


class IRateLimitManager(Interface):
    async def __call__(self):
        """This method should handle all rate limiting logic for a specific
        context
        """
        pass
