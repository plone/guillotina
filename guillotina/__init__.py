# load the patch before anything else.

from guillotina import glogging
from guillotina._cache import BEHAVIOR_CACHE  # noqa
from guillotina._cache import FACTORY_CACHE  # noqa
from guillotina._cache import PERMISSIONS_CACHE  # noqa
from guillotina._cache import SCHEMA_CACHE  # noqa
from guillotina._settings import app_settings  # noqa
from guillotina.i18n import default_message_factory as _  # noqa
from zope.interface import Interface  # noqa

import os
import pkg_resources


__version__ = pkg_resources.get_distribution("guillotina").version


# create logging
logger = glogging.getLogger("guillotina")


if os.environ.get("GDEBUG", "").lower() in ("true", "t", "1"):  # pragma: no cover
    # patches for extra debugging....
    import asyncpg
    import time

    original_execute = asyncpg.connection.Connection._do_execute
    logger.warning("RUNNING IN DEBUG MODE")

    def _record(query, duration):
        # log each query on the transaction object...
        try:
            from guillotina.transactions import get_transaction

            txn = get_transaction()
            if txn:
                if not hasattr(txn, "_queries"):
                    txn._queries = {}
                if query not in txn._queries:
                    txn._queries[query] = [0, 0.0]
                txn._queries[query][0] += 1
                txn._queries[query][1] += duration
        except AttributeError:
            pass

    async def _do_execute(self, query, *args, **kwargs):
        start = time.time()
        result = await original_execute(self, query, *args, **kwargs)
        end = time.time()
        _record(query, end - start)
        return result

    asyncpg.connection.Connection._do_execute = _do_execute  # type: ignore

    original_bind_execute = asyncpg.prepared_stmt.PreparedStatement._PreparedStatement__bind_execute

    async def __bind_execute(self, *args, **kwargs):
        start = time.time()
        result = await original_bind_execute(self, *args, **kwargs)
        end = time.time()
        _record(self._query, end - start)
        return result

    asyncpg.prepared_stmt.PreparedStatement._PreparedStatement__bind_execute = __bind_execute  # type: ignore
