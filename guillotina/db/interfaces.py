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

    async def finalize():
        pass

    async def initialize(loop):
        pass

    async def remove():
        pass

    async def load(txn, oid):
        pass

    async def store(oid, old_serial, writer, obj, txn):
        pass

    async def delete(txn, oid):
        pass

    async def get_next_tid(txn):
        pass

    async def start_transaction(txn):
        pass

    async def get_current_tid(txn):
        pass

    async def get_conflicts(txn, full=False):
        pass

    async def commit(txn):
        pass

    async def abort(txn):
        pass

    async def keys(txn, oid):
        pass

    async def get_child(txn, parent_oid, id):
        pass

    async def has_key(txn, parent_oid, id):
        pass

    async def len(txn, oid):
        pass

    async def items(txn, oid):
        pass

    async def get_annotation(txn, oid, id):
        pass

    async def get_annotation_keys(txn, oid):
        pass

    async def write_blob_chunk(txn, bid, oid, chunk_index, data):
        pass

    async def read_blob_chunk(txn, bid, chunk=0):
        pass

    async def read_blob_chunks(txn, bid):
        pass

    async def del_blob(txn, bid):
        pass

    async def get_total_number_of_objects(txn):
        pass

    async def get_total_number_of_resources(txn):
        pass


class IPostgresStorage(IStorage):
    pass


class ITransactionStrategy(Interface):

    async def tpc_begin():
        '''
        Begin transaction, should set ._tid on transaction if supports transactions
        '''

    async def tpc_vote():
        '''
        Returns true if no conflicts, false if conflicts
        '''

    async def tpc_finish():
        '''
        Finish the transaction, committing transaction
        '''


class IDBTransactionStrategy(ITransactionStrategy):
    pass


class ILockingStrategy(ITransactionStrategy):
    async def lock(obj):
        pass

    async def unlock(obj):
        pass


class IStorageCache(Interface):

    async def clear():
        pass

    async def get(oid=None, container=None, id=None, variant=None):
        pass

    async def set(value, oid=None, container=None, id=None, variant=None):
        pass

    async def delete(key):
        pass

    async def delete_all(keys):
        pass

    async def close():
        pass
