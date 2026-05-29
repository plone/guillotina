import asyncio
import logging

from zope.interface import implementer

from guillotina import app_settings
from guillotina.component import get_utility
from guillotina.contrib.oauth.interfaces import IOAuthStorageUtility
from guillotina.contrib.oauth.storage.pg.repository import cleanup_expired
from guillotina.contrib.oauth.storage.pg.schema import OAUTH_DDL
from guillotina.db.interfaces import IPostgresStorage
from guillotina.interfaces import IApplication, IDatabase


logger = logging.getLogger("guillotina.contrib.oauth")

_ddl_lock = asyncio.Lock()
_ddl_initialized = False

OAUTH_STORAGE_DEFAULTS = {
    "cleanup_interval": 900,
    "cleanup_batch_size": 5000,
}


def get_oauth_storage_settings():
    settings = dict(OAUTH_STORAGE_DEFAULTS)
    oauth = app_settings.get("oauth") or {}
    for key in OAUTH_STORAGE_DEFAULTS:
        if key in oauth:
            settings[key] = oauth[key]
    try:
        utility = get_utility(IOAuthStorageUtility)
        utility_settings = getattr(utility, "_settings", None) or {}
        for key in OAUTH_STORAGE_DEFAULTS:
            if key in utility_settings:
                settings[key] = utility_settings[key]
    except Exception:
        pass
    return settings


async def ensure_oauth_tables(storage):
    import asyncpg.exceptions

    global _ddl_initialized
    async with _ddl_lock:
        if _ddl_initialized:
            return
        async with storage.pool.acquire() as conn:
            for ddl in OAUTH_DDL:
                for attempt in range(3):
                    try:
                        await conn.execute(ddl)
                        break
                    except asyncpg.exceptions.UniqueViolationError:
                        if attempt == 2:
                            raise
                        await asyncio.sleep(0.05)
        _ddl_initialized = True


@implementer(IOAuthStorageUtility)
class OAuthStorageUtility:
    def __init__(self, settings=None):
        self._settings = settings or {}
        self._task = None
        self._closing = False

    async def initialize(self, app=None):
        initialized = False
        root = get_utility(IApplication, name="root")
        for _id, db in root:
            if not IDatabase.providedBy(db):
                continue
            tm = db.get_transaction_manager()
            if not IPostgresStorage.providedBy(tm.storage):
                continue
            await ensure_oauth_tables(tm.storage)
            initialized = True
        if initialized:
            self._closing = False
            self._task = asyncio.create_task(self._cleanup_loop())
            logger.info("OAuth storage initialized (PostgreSQL)")
        else:
            logger.info("OAuth PostgreSQL tables skipped (no PostgreSQL database found)")

    async def finalize(self, app=None):
        self._closing = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _cleanup_loop(self):
        storage_settings = get_oauth_storage_settings()
        interval = storage_settings.get("cleanup_interval", 900)
        batch_size = storage_settings.get("cleanup_batch_size", 5000)
        while not self._closing:
            try:
                await asyncio.sleep(interval)
                await self.run_cleanup(batch_size=batch_size)
            except asyncio.CancelledError:
                return
            except Exception:
                logger.warning("OAuth cleanup failed", exc_info=True)

    async def run_cleanup(self, batch_size=5000):
        root = get_utility(IApplication, name="root")
        for _id, db in root:
            if not IDatabase.providedBy(db):
                continue
            tm = db.get_transaction_manager()
            if not IPostgresStorage.providedBy(tm.storage):
                continue
            async with tm.storage.pool.acquire() as conn:
                await cleanup_expired(conn, batch_size=batch_size)
