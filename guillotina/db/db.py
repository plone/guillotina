# -*- encoding: utf-8 -*-
from aiohttp.test_utils import make_mocked_request
from guillotina.content import Folder
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.db.transaction_manager import TransactionManager
from guillotina.interfaces import IDatabase
from zope.interface import implementer_only

import asyncio


@implementer_only(IDatabase, IBaseObject)
class Root(Folder):

    __name__ = None
    portal_type = 'GuillotinaDBRoot'

    def __repr__(self):
        return "<Database %d>" % id(self)


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
        self.request = request

        try:
            assert request._tm.get() == t
            await t.get(0)
        except KeyError:
            root = Root()
            root._p_oid = 0
            t.register(root)

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
