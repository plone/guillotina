# -*- encoding: utf-8 -*-
from aiohttp.test_utils import make_mocked_request
from guillotina.content import Folder
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.db.transaction_manager import TransactionManager
from guillotina.interfaces import IDatabase
from guillotina.db import ROOT_ID
from zope.interface import implementer_only

import asyncio


@implementer_only(IDatabase, IBaseObject)
class Root(Folder):

    __name__ = None
    __cache__ = 0
    portal_type = 'GuillotinaDBRoot'

    def __repr__(self):
        return "<Database %d>" % id(self)




class GuillotinaDB(object):

    def __init__(self,
                 storage,
                 remote_cache=None,
                 database_name='unnamed'):
        """Create an object database.
        """

        self.remote_cache = remote_cache
        self.storage = storage
        if remote_cache is not None:
            self.storage.use_cache(remote_cache)
        self.database_name = database_name

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
            t.register(root, new_oid=ROOT_ID)

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
