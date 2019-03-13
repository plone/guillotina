

class BaseStorage:

    _cache_strategy = 'dummy'
    _read_only = False
    _transaction_strategy = 'resolve'
    _supports_unique_constraints = False

    def __init__(self, read_only=False, transaction_strategy='resolve',
                 cache_strategy='dummy'):
        self._read_only = read_only
        self._transaction_strategy = transaction_strategy
        self._cache_strategy = cache_strategy
        self._hits = 0
        self._misses = 0
        self._stored = 0

    @property
    def supports_unique_constraints(self):
        return self._supports_unique_constraints

    def read_only(self):
        return self._read_only

    async def finalize(self):
        raise NotImplemented()  # pragma: no cover

    async def initialize(self, loop=None, **kw):
        raise NotImplemented()  # pragma: no cover

    async def open(self):
        raise NotImplemented()  # pragma: no cover

    async def close(self, con):
        raise NotImplemented()  # pragma: no cover

    async def load(self, txn, oid):
        raise NotImplemented()  # pragma: no cover

    async def store(self, oid, old_serial, writer, obj, txn):
        raise NotImplemented()  # pragma: no cover

    async def delete(self, txn, oid):
        raise NotImplemented()  # pragma: no cover

    async def get_next_tid(self, txn):
        raise NotImplemented()  # pragma: no cover

    async def get_current_tid(self, txn):
        raise NotImplemented()  # pragma: no cover

    async def get_one_row(self, smt, *args):
        raise NotImplemented()  # pragma: no cover

    async def start_transaction(self, txn, retries=0):
        raise NotImplemented()  # pragma: no cover

    async def get_conflicts(self, txn):
        raise NotImplemented()  # pragma: no cover

    async def commit(self, transaction):
        raise NotImplemented()  # pragma: no cover

    async def abort(self, transaction):
        raise NotImplemented()  # pragma: no cover

    async def get_page_of_keys(self, txn, oid, page=1, page_size=1000):
        raise NotImplemented()  # pragma: no cover

    async def keys(self, txn, oid):
        raise NotImplemented()  # pragma: no cover

    async def get_child(self, txn, parent_oid, id):
        raise NotImplemented()  # pragma: no cover

    async def has_key(self, txn, parent_oid, id):
        raise NotImplemented()  # pragma: no cover

    async def len(self, txn, oid):
        raise NotImplemented()  # pragma: no cover

    async def items(self, txn, oid):
        raise NotImplemented()  # pragma: no cover

    async def get_annotation(self, txn, oid, id):
        raise NotImplemented()  # pragma: no cover

    async def get_annotation_keys(self, txn, oid):
        raise NotImplemented()  # pragma: no cover

    async def write_blob_chunk(self, txn, bid, oid, chunk_index, data):
        raise NotImplemented()  # pragma: no cover

    async def read_blob_chunk(self, txn, bid, chunk=0):
        raise NotImplemented()  # pragma: no cover

    async def read_blob_chunks(self, txn, bid):
        raise NotImplemented()  # pragma: no cover

    async def del_blob(self, txn, bid):
        raise NotImplemented()  # pragma: no cover

    async def get_total_number_of_objects(self, txn):
        raise NotImplemented()  # pragma: no cover

    async def get_total_number_of_resources(self, txn):
        raise NotImplemented()  # pragma: no cover

    async def get_total_resources_of_type(self, txn, type_):
        raise NotImplemented()  # pragma: no cover

    async def _get_page_resources_of_type(self, txn, type_, page, page_size):
        raise NotImplemented()  # pragma: no cover

    async def vacuum(self):
        raise NotImplemented()  # pragma: no cover
