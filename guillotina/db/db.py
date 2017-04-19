# -*- encoding: utf-8 -*-
from aiohttp.test_utils import make_mocked_request
from guillotina.content import Folder
from guillotina.db import ROOT_ID
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.db.transaction_manager import TransactionManager
from guillotina.interfaces import IDatabase
from zope.interface import implementer_only


@implementer_only(IDatabase, IBaseObject)
class Root(Folder):

    __name__ = None
    __cache__ = 0
    type_name = 'GuillotinaDBRoot'

    def __repr__(self):
        return "<Database %d>" % id(self)


class GuillotinaDB(object):

    def __init__(self,
                 storage,
                 remote_cache=None,
                 database_name='unnamed'):
        """
        Create an object database.

        Database object is persistent through the application
        """
        self._tm = None
        self._remote_cache = remote_cache
        self._storage = storage
        if remote_cache is not None:
            self._storage.use_cache(remote_cache)
        self._database_name = database_name

    @property
    def storage(self):
        return self._storage

    async def initialize(self):
        """
        create root object if necessary
        """
        request = make_mocked_request('POST', '/')
        request._db_write_enabled = True
        request._tm = TransactionManager(self._storage)
        t = await request._tm.begin(request=request)
        self.request = request

        try:
            assert request._tm.get() == t
            await t.get(ROOT_ID)
        except KeyError:
            root = Root()
            t.register(root, new_oid=ROOT_ID)

        await request._tm.commit()

    async def open(self):
        """Return a database Connection for use by application code.
        """
        return await self._storage.open()

    async def close(self, conn):
        await self._storage.close(conn)

    async def finalize(self):
        await self._storage.finalize()

    def new_transaction_manager(self):
        """
        New transaction manager for every request
        """
        tm = TransactionManager(self._storage)
        self._tm = tm
        return tm
