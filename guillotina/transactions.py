from guillotina import task_vars
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionManager

import logging
import typing


logger = logging.getLogger("guillotina")


async def commit(*, txn: typing.Optional[ITransaction] = None, warn=True) -> None:
    """
    Commit the current active transaction.

    :param txn: transaction to commit
    """
    tm = None
    try:
        tm = get_tm()
    except AttributeError:
        if warn:
            logger.warning("Could not locate transaction manager to commit", exc_info=True)

    if tm is not None:
        await tm.commit(txn=txn)


async def abort(*, txn: typing.Optional[ITransaction] = None) -> None:
    """
    Abort the current active transaction.

    :param txn: transaction to abort
    """
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

    Example::

        with get_tm().transaction() as txn:  # begin transaction txn

            # do something

        # transaction txn commits or raises ConflictError

    """
    return task_vars.tm.get()


def get_transaction() -> typing.Optional[ITransaction]:
    """
    Return the current active transaction.
    """
    return task_vars.txn.get()


class transaction:  # noqa: N801
    """
    Execute a transaction as async context manager and
    automatically close connection after done.

    >>> async with transaction() as txn:
    >>>   pass

    :param db: db to operate transaction on
    :param tm: transaction manager to retrieve transaction from
    :param abort_when_done: Abort transaction when done (defaults to false)
    :param adopt_parent_txn: If this is a sub-transaction, use parent's registered objects
    :param execute_futures: Execute registered futures with transaction after done (defaults to true)
    :param read_only: Is this a read_only txn? (default to false)
    """

    def __init__(
        self,
        *,
        db=None,
        tm=None,
        abort_when_done=False,
        adopt_parent_txn=False,
        execute_futures=True,
        read_only=False,
    ):
        if db is not None and tm is None:
            tm = db.get_transaction_manager()
        self.tm = tm or get_tm()
        self.abort_when_done = abort_when_done
        self.previous_tm = self.previous_txn = self.txn = None
        self.adopt_parent_txn = adopt_parent_txn
        self.execute_futures = execute_futures
        self.adopted = []
        self.read_only = read_only

    async def __aenter__(self):
        txn = get_transaction()
        if txn is not None:
            self.previous_txn = txn
        tm = get_tm()
        if tm is not None:
            self.previous_tm = tm

        self.txn = await self.tm.begin(read_only=self.read_only)
        # these should be restored after
        task_vars.tm.set(self.tm)
        task_vars.txn.set(self.txn)
        return self.txn

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
                self.txn.modified = {**self.previous_txn.modified, **self.txn.modified}
                self.txn.deleted = {**self.previous_txn.deleted, **self.txn.deleted}
                self.txn.added = {**self.previous_txn.added, **self.txn.added}

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

        if self.execute_futures:
            from guillotina.utils import execute

            execute.execute_futures()

        if self.previous_txn is not None:
            task_vars.txn.set(self.previous_txn)
        if self.previous_tm is not None:
            task_vars.tm.set(self.previous_tm)


managed_transaction = transaction  # noqa
