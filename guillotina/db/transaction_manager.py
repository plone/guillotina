from guillotina.db import ROOT_ID
from guillotina.db.transaction import Transaction
from guillotina.utils import get_authenticated_user_id
from guillotina.utils import get_current_request
from queue import LifoQueue


class TransactionManager(object):
    """Transaction manager for storing the managed transaction in the
    current request

    """

    def __init__(self, storage):
        # Guillotine Storage
        self._storage = storage
        # Last transaction created
        self._txn = None
        # Pool of transactions
        self._pool = None
        self._db_conn = None
        self.request = None

    async def root(self):
        return await self._txn.get(ROOT_ID)

    async def begin(self, request=None):
        """Starts a new transaction.
        """

        self._db_conn = await self._storage.open()

        if request is None:
            if self.request is None:
                self.request = get_current_request()
            request = self.request
        request._tm = self  # register it here with request...

        user = get_authenticated_user_id(request)
        if self._txn is not None:
            if self._pool is None:
                self._pool = LifoQueue()
            # Save the actual transaction and start a new one
            self._pool.put(self._txn)

        self._txn = txn = Transaction(self, request=request)

        # CACHE!!

        if user is not None:
            txn.user = user
        await txn.tpc_begin(self._db_conn)

        return txn

    async def commit(self):
        """ Commit the last transaction
        """
        txn = self.get()
        if txn is not None:
            await txn.commit()
        await self._storage.close(txn._db_conn)
        self._txn = None
        self._db_conn = None
        if self._pool is not None and self._pool.qsize():
            self._txn = self._pool.get_nowait()
            self._db_conn = self._txn._db_conn

    async def abort(self):
        """ Abort the last transaction
        """
        txn = self.get()
        if txn is not None:
            await txn.abort()
        await self._storage.close(txn._db_conn)
        self._txn = None
        self._db_conn = None
        if self._pool is not None and self._pool.qsize():
            self._txn = self._pool.get_nowait()
            self._db_conn = self._txn._db_conn

    def get(self):
        """Return the current request specific transaction
        """
        if self._txn:
            return self._txn
        if self._pool is not None and self._pool.qsize():
            self._txn = self._pool.get_nowait()
            return self._txn
        return None
