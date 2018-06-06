from guillotina.interfaces import IDatabase
from zope.interface import Interface


class IPartition(Interface):
    """Get the partition of the object"""


class IWriter(Interface):
    """Serializes the object for DB storage"""


class ITransaction(Interface):
    pass


class IStorage(Interface):
    '''
    interface storage adapters must implement
    '''

    async def finalize():  # type: ignore
        '''
        Run cleanup
        '''

    async def initialize(loop):
        '''
        Initialize database
        '''

    async def remove():  # type: ignore
        '''
        Remove database
        '''

    async def load(txn, oid):
        '''
        load ob from oid
        '''

    async def store(oid, old_serial, writer, obj, txn):
        '''
        store oid with obj
        '''

    async def delete(txn, oid):
        '''
        delete ob by oid
        '''

    async def get_next_tid(txn):
        '''
        get next transaction id
        '''

    async def start_transaction(txn):
        '''
        start transaction
        '''

    async def get_current_tid(txn):
        '''
        Get current tid
        '''

    async def get_conflicts(txn, full=False):
        '''
        get conflicted ob writes
        '''

    async def commit(txn):
        '''
        Commit current transaction
        '''

    async def abort(txn):
        '''
        abort transaction
        '''

    async def keys(txn, oid):
        '''
        get keys for oid
        '''

    async def get_child(txn, parent_oid, id):
        '''
        get child of parent oid
        '''

    async def has_key(txn, parent_oid, id):
        '''
        check if key exists
        '''

    async def len(txn, oid):
        '''
        get length of folder
        '''

    async def items(txn, oid):
        '''
        get items in a folder
        '''

    async def get_annotation(txn, oid, id):
        '''
        get annotation
        '''

    async def get_annotation_keys(txn, oid):
        '''
        get annotation keys
        '''

    async def write_blob_chunk(txn, bid, oid, chunk_index, data):
        '''
        write blob chunk
        '''

    async def read_blob_chunk(txn, bid, chunk=0):
        '''
        read blob chunk
        '''

    async def read_blob_chunks(txn, bid):
        '''
        read blob chunks
        '''

    async def del_blob(txn, bid):
        '''
        delete blob
        '''


class IPostgresStorage(IStorage):
    pass


class ITransactionStrategy(Interface):

    async def tpc_begin():  # type: ignore
        '''
        Begin transaction, should set ._tid on transaction if supports transactions
        '''

    async def tpc_vote():  # type: ignore
        '''
        Returns true if no conflicts, false if conflicts
        '''

    async def tpc_finish():  # type: ignore
        '''
        Finish the transaction, committing transaction
        '''


class IDBTransactionStrategy(ITransactionStrategy):
    pass


class IStorageCache(Interface):

    async def clear():  # type: ignore
        '''
        clear cache
        '''

    async def get(oid=None, container=None, id=None, variant=None):
        '''
        get cached object
        '''

    async def set(value, oid=None, container=None, id=None, variant=None):
        '''
        set cached data
        '''

    async def delete(key):
        '''
        delete cache key
        '''

    async def delete_all(keys):
        '''
        delete list of keys
        '''

    async def close():  # type: ignore
        '''
        close the cache
        '''


class IDatabaseManager(Interface):
    async def get_names() -> list:  # type: ignore
        '''
        Return a list of available databases
        '''

    async def create(name: str) -> IStorage:
        '''
        Create a new database on the storage
        '''

    async def delete(name: str):  # type: ignore
        '''
        Delete database on the storage
        '''

    async def get_database(name: str) -> IDatabase:
        '''
        Return storage instance for database
        '''

    async def exists(name: str) -> bool:
        '''
        Return whether a db exists or not
        '''
