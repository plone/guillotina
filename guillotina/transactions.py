import logging
import typing

from guillotina._settings import tm_var
from guillotina._settings import txn_var
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionManager
from guillotina.exceptions import RequestNotFound
from guillotina.interfaces import IRequest
from guillotina.utils import get_current_request


logger = logging.getLogger('guillotina')


def _safe_get_request(request: typing.Optional[IRequest]=None) -> typing.Optional[IRequest]:
    if request is None:
        try:
            request = get_current_request()
        except RequestNotFound:
            pass
    return request


async def commit(*, txn: typing.Optional[ITransaction]=None, warn=True) -> None:
    '''
    Commit the current active transaction.

    :param request: request object transaction is connected to
    '''
    tm = None
    try:
        tm = get_tm()
    except AttributeError:
        if warn:
            logger.warning('Could not locate transaction manager to commit', exc_info=True)

    if tm is not None:
        await tm.commit(txn=txn)


async def abort(*, txn: typing.Optional[ITransaction]=None) -> None:
    '''
    Abort the current active transaction.

    :param request: request object transaction is connected to
    '''
    tm = None
    try:
        tm = get_tm()
    except AttributeError:
        # not part of transaction, ignore
        pass
    if tm is not None:
        await tm.abort(txn=txn)


def get_tm() -> typing.Optional[ITransactionManager]:
    """Return shared transaction manager (from request)

    This is used together with "with" syntax for wrapping mutating
    code into a request owned transaction.

    :param request: request owning the transaction

    Example::

        with get_tm().transaction() as txn:  # begin transaction txn

            # do something

        # transaction txn commits or raises ConflictError

    """
    return typing.cast(ITransactionManager, tm_var.get())


def get_transaction() -> typing.Optional[ITransaction]:
    '''
    Return the current active transaction.

    :param request: request object transaction is connected to

    '''
    return typing.cast(ITransaction, txn_var.get())


class transaction:  # noqa: N801
    '''
    Execute a transaction as async context manager and
    automatically close connection after done.

    >>> async with transaction() as txn:
    >>>   pass

    :param request: request object to connect transaction with
    :param db: transaction manager to retrieve transaction from
    :param tm: transaction manager to retrieve transaction from
    :param write: Does this write to database? (defaults to false)
    :param abort_when_done: Abort transaction when done (defaults to false)
    :param adopt_parent_txn: If this is a sub-transaction, use parent's registered objects
    :param execute_futures: Execute registered futures with transaction after done (defaults to true)
    '''

    def __init__(self, *, db=None, tm=None, write=False, abort_when_done=False,
                 adopt_parent_txn=False, execute_futures=True):
        self.request = _safe_get_request()
        if db is not None and tm is None:
            tm = db.get_transaction_manager()
        self.tm = tm or get_tm()
        self.write = write
        self.abort_when_done = abort_when_done
        self.previous_txn = self.txn = self.previous_write_setting = None
        self.adopt_parent_txn = adopt_parent_txn
        self.execute_futures = execute_futures
        self.adopted = []

    async def __aenter__(self):
        self.previous_write_setting = getattr(self.request, '_db_write_enabled', False)
        if self.write and self.request is not None:
            self.request._db_write_enabled = True

        txn = get_transaction()
        if txn is not None:
            self.previous_txn = txn

        self.txn = await self.tm.begin()
        # these should be restored after
        tm_var.set(self.tm)
        txn_var.set(self.txn)
        return self.txn

    def adopt_objects(self, obs, txn):
        for oid, ob in obs.items():
            self.adopted.append(ob)
            ob.__txn__ = txn

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
                    ob.__txn__ = self.previous_txn

        if self.request is not None:
            if self.previous_write_setting is not None:
                self.request._db_write_enabled = self.previous_write_setting

            if self.execute_futures:
                self.request.execute_futures()


managed_transaction = transaction  # noqa
