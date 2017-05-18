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
    try:
        request = _safe_get_request(request)
        await get_tm(request).commit(request)
    except AttributeError as e:
        if warn:
            logger.warn('Could not locate transaction manager to commit', exc_info=True)


async def abort(request=None):
    try:
        tm = get_tm(request)
        await tm.abort(request)
    except AttributeError:
        # not part of transaction, ignore
        pass
        # logger.warn('Could not locate transaction manager to abort', exc_info=True)


def get_tm(request=None):
    """Return shared transaction manager (from request)

    This is used together with "with" syntax for wrapping mutating
    code into a request owned transaction.

    :param request: request owning the transaction

    Example::

        with get_tm(request) as txn:  # begin transaction txn

            # do something

        # transaction txn commits or raises ConflictError

    """
    return _safe_get_request(request)._tm


def get_transaction(request=None):
    req = _safe_get_request(request)
    return req._tm.get(req)



class managed_transaction:
    def __init__(self, request=None, tm=None, write=False, abort_when_done=False):
        self.request = _safe_get_request(request)
        if tm is None:
            tm = request._tm
        self.tm = tm
        self.write = write
        self.abort_when_done = abort_when_done
        self.previous_txn = self.txn = self.previous_write_setting = None

    async def __aenter__(self):
        if self.request is not None:
            self.previous_txn = self.request._txn
            self.previous_write_setting = getattr(self.request, '_db_write_enabled', False)
            if self.write:
                self.request._db_write_enabled = True
        self.txn = await self.tm.begin(request=self.request)

    async def __aexit__(self, exc_type, exc, tb):
        if self.abort_when_done:
            await self.tm.abort(txn=self.txn)
        else:
            await self.tm.commit(txn=self.txn)
        if self.request is not None:
            self.request._txn = self.previous_txn
            self.request._db_write_enabled = self.previous_write_setting
