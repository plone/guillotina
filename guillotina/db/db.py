from guillotina.content import Folder
from guillotina.db import ROOT_ID
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.db.transaction_manager import TransactionManager
from guillotina.interfaces import IDatabase
from guillotina.tests.utils import make_mocked_request
from zope.interface import implementer_only


@implementer_only(IDatabase, IBaseObject)
class Root(Folder):

    __name__ = None
    __immutable_cache__ = True
    __db_id__ = None
    type_name = 'GuillotinaDBRoot'

    def __init__(self, db_id):
        super().__init__()
        self.__db_id__ = db_id

    def __repr__(self):
        return "<Database %d>" % id(self)


class GuillotinaDB(object):

    def __init__(self,
                 storage,
                 database_name='unnamed'):
        """
        Create an object database.

        Database object is persistent through the application
        """
        self._tm = None
        self._storage = storage
        self._database_name = database_name
        self._tm = None

    @property
    def storage(self):
        return self._storage

    async def initialize(self):
        """
        create root object if necessary
        """
        request = make_mocked_request('POST', '/')
        request._db_write_enabled = True
        tm = request._tm = self.get_transaction_manager()
        txn = await tm.begin(request=request)
        # for get_current_request magic
        self.request = request

        commit = False
        try:
            assert tm.get(request=request) == txn
            root = await txn.get(ROOT_ID)
            if root.__db_id__ is None:
                root.__db_id__ = self._database_name
                txn.register(root)
                commit = True
        except KeyError:
            root = Root(self._database_name)
            txn.register(root, new_oid=ROOT_ID)
            commit = True

        if commit:
            await tm.commit(txn=txn)
        else:
            await tm.abort(txn=txn)

    async def open(self):
        """Return a database Connection for use by application code.
        """
        return await self._storage.open()

    async def close(self, conn):
        await self._storage.close(conn)

    async def finalize(self):
        await self._storage.finalize()

    def get_transaction_manager(self):
        """
        New transaction manager for every request
        """
        if self._tm is None:
            self._tm = TransactionManager(self._storage)
        return self._tm
