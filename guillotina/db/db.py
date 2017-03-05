# -*- encoding: utf-8 -*-
from aiohttp.test_utils import make_mocked_request
from guillotina import configure
from guillotina.browser import View
from guillotina.content import Folder
from guillotina.interfaces import IDatabase
from guillotina.db.transaction_manager import TransactionManager

import asyncio


@configure.contenttype(
    portal_type="Database",
    schema=IDatabase,
    behaviors=[])
class Database(Folder):

    __name__ = 'Root'
    portal_type = 'Database'


class RootAddOperation(View):
    async def __call__(self):
        try:
            # We have a transaction as conexgt
            assert self.request._tm.get() == self.context
            await self.context.get(0)
        except KeyError:
            root = Database()
            root._p_oid = 0
            self.context.register(root)


class GuillotinaDB(object):

    def __init__(self,
                 storage,
                 cache_size=400,
                 cache_size_bytes=0,
                 database_name='unnamed'):
        """Create an object database.
        """

        self.opened = None
        # Allocate lock.
        self._lock = asyncio.Lock()
        self._cache_size = cache_size
        self._cache_size_bytes = cache_size_bytes
        self.storage = storage
        self.database_name = database_name
        self._conn = None

    async def initialize(self):
        # Make sure we have a root:
        request = make_mocked_request('POST', '/')
        request._db_write_enabled = True
        request._tm = TransactionManager(self.storage)
        t = await request._tm.begin(request=request)
        operation = RootAddOperation(t, request)
        await operation()
        await request._tm.commit()

    async def open(self):
        """Return a database Connection for use by application code.
        """
        return await self.storage.open()

    async def close(self, conn):
        await self.storage.close(conn)

    async def finalize(self):
        await self.storage.finalize()

    def new_transaction_manager(self):
        return TransactionManager(self.storage)
