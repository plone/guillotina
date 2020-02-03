import logging
import uuid
from guillotina import app_settings


logger = logging.getLogger("guillotina")


class RedisSessionManagerUtility:

    def __init__(self, settings=None, loop=None):
        self._loop = loop
        self._ttl = app_settings.get('jwt', {}).get('token_expiration', 3660)
        self._prefix = settings.get('prefix', 'session')
        self._driver = None
        self._initialized = False

    async def initialize(self, app=None):
        from guillotina.contrib import redis
        self._driver = await redis.get_driver()
        await self._driver.initialize(self._loop)
        self._initialized = True

    async def finalize(self):
        self._initialized = False

    async def new_session(self, ident: str, data: str = '') -> str:
        session = uuid.uuid4().hex
        session_key = f"{self._prefix}:{ident}:{session}"
        await self._driver.set(session_key, data, expire=self._ttl)
        return session

    async def exist_session(self, ident: str, session: str) -> bool:
        if session is None:
            return False
        if ident is None:
            return False
        session_key = f"{self._prefix}:{ident}:{session}"
        value = await self._driver.get(session_key)
        if value is not None:
            return True
        else:
            return False

    async def drop_session(self, ident: str, session: str):
        session_key = f"{self._prefix}:{ident}:{session}"
        value = await self._driver.get(session_key)
        if value is not None:
            await self._driver.delete(session_key)
        else:
            raise KeyError('Invalid session')

    async def refresh_session(self, ident: str, session: str):
        session_key = f"{self._prefix}:{ident}:{session}"
        value = await self._driver.get(session_key)
        if value is not None:
            await self._driver.expire(session_key, self._ttl)
            return session
        else:
            raise KeyError('Invalid session')

    async def list_sessions(self, ident: str):
        if ident is None:
            return []
        session_key = f"{self._prefix}:{ident}"
        value = await self._driver.keys_startswith(session_key)
        return [x.split(b':')[2].decode('utf-8') for x in value]

    async def get_session(self, ident: str, session: str):
        if ident is None:
            return []
        session_key = f"{self._prefix}:{ident}:{session}"
        value = await self._driver.get(session_key)
        return value.decode('utf-8')
