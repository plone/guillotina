from guillotina.exceptions import RequestNotFound
from guillotina.utils import get_current_request

import logging


logger = logging.getLogger('guillotina')


def _safe_get_request(request):
    if request is None:
        try:
            request = get_current_request()
        except RequestNotFound:
            pass
    return request


async def commit(request=None, warn=True):
    '''
    Commit the current active transaction.

    :param request: request object transaction is connected to
    '''
    tm = None
    try:
        request = _safe_get_request(request)
        tm = get_tm(request)
    except AttributeError:
        if warn:
            logger.warning('Could not locate transaction manager to commit', exc_info=True)

    if tm is not None:
        await tm.commit(request)

async def abort(request=None):
    '''
    Abort the current active transaction.

    :param request: request object transaction is connected to
    '''
    tm = None
    try:
        tm = get_tm(request)
    except AttributeError:
        # not part of transaction, ignore
        pass
    if tm is not None:
        await tm.abort(request)


def get_tm(request=None):
    """Return shared transaction manager (from request)

    This is used together with "with" syntax for wrapping mutating
    code into a request owned transaction.

    :param request: request owning the transaction

    Example::

        with get_tm(request).transaction() as txn:  # begin transaction txn

            # do something

        # transaction txn commits or raises ConflictError

    """
    return _safe_get_request(request)._tm


def get_transaction(request=None):
    '''
    Return the current active transaction.

    :param request: request object transaction is connected to

    '''
    req = _safe_get_request(request)
    return req._tm.get(req)


class managed_transaction:  # noqa: N801
    '''
    Execute a transaction as async context manager and
    automatically close connection after done.

    >>> async with managed_transaction() as txn:
    >>>   pass

    :param request: request object to connect transaction with
    :param tm: transaction manager to retrieve transaction from
    :param write: Does this write to database? (defaults to false)
    :param abort_when_done: Abort transaction when done (defaults to false)
    :param adopt_parent_txn: If this is a sub-transaction, use parent's registered objects
    :param execute_futures: Execute registered futures with transaction after done (defaults to true)
    '''

    def __init__(self, request=None, tm=None, write=False, abort_when_done=False,
                 adopt_parent_txn=False, execute_futures=True):
        self.request = _safe_get_request(request)
        if tm is None:
            tm = request._tm
        self.tm = tm
        self.write = write
        self.abort_when_done = abort_when_done
        self.previous_txn = self.txn = self.previous_write_setting = None
        self.adopt_parent_txn = adopt_parent_txn
        self.execute_futures = execute_futures
        self.adopted = []

    async def __aenter__(self):
        if self.request is not None and hasattr(self.request, '_txn'):
            self.previous_txn = self.request._txn
            self.previous_write_setting = getattr(self.request, '_db_write_enabled', False)
            if self.write:
                self.request._db_write_enabled = True
        self.txn = await self.tm.begin(request=self.request)
        return self.txn

    def adopt_objects(self, obs, txn):
        for oid, ob in obs.items():
            self.adopted.append(ob)
            ob._p_jar = txn

    async def __aexit__(self, exc_type, exc, tb):
        if self.adopt_parent_txn and self.previous_txn is not None:
            # take on parent's modified, added, deleted objects if necessary
            # before we commit or abort this transaction.
            # this is necessary because inside this block, the outer transaction
            # could have been attached to an object that changed.
            # we're ready to commit and we want to potentially commit everything
            # where, we we're adopted those objects with this transaction
            if self.previous_txn != self.txn:
                # try adopting currently registered objects
                self.txn.modified = {
                    **self.previous_txn.modified,
                    **self.txn.modified}
                self.txn.deleted = {
                    **self.previous_txn.deleted,
                    **self.txn.deleted}
                self.txn.added = {
                    **self.previous_txn.added,
                    **self.txn.added}

                self.adopt_objects(self.previous_txn.modified, self.txn)
                self.adopt_objects(self.previous_txn.deleted, self.txn)
                self.adopt_objects(self.previous_txn.added, self.txn)

        if self.abort_when_done:
            await self.tm.abort(txn=self.txn)
        else:
            await self.tm.commit(txn=self.txn)

        if self.adopt_parent_txn and self.previous_txn is not None:
            # restore transaction ownership of item from adoption done above
            if self.previous_txn != self.txn:
                # we adopted previously detetected transaction so now
                # we need to clear changed objects and restore ownership
                self.previous_txn.modified = {}
                self.previous_txn.deleted = {}
                self.previous_txn.added = {}

                for ob in self.adopted:
                    ob._p_jar = self.previous_txn

        if self.request is not None:
            if self.previous_txn is not None:
                # we do not want to overwrite _txn if is it None since we can
                # reuse transaction objects and we don't want to screw up
                # stale objects that reference dangling transactions with no
                # db connection
                self.request._txn = self.previous_txn
            if self.previous_write_setting is not None:
                self.request._db_write_enabled = self.previous_write_setting

        if self.request is not None and self.execute_futures:
            self.request.execute_futures()
