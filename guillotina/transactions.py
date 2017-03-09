import logging


logger = logging.getLogger('guillotina')


async def commit(request):
    try:
        await request._tm.commit()
    except AttributeError as e:
        logger.warn('Could not locate transaction manager to commit', exc_info=True)


async def abort(request):
    try:
        await request._tm.abort()
    except AttributeError:
        # not part of transaction, ignore
        pass
        # logger.warn('Could not locate transaction manager to abort', exc_info=True)


def get_tm(request):
    """Return shared transaction manager (from request)

    This is used together with "with" syntax for wrapping mutating
    code into a request owned transaction.

    :param request: request owning the transaction

    Example::

        with get_tm(request) as txn:  # begin transaction txn

            # do something

        # transaction txn commits or raises ConflictError

    """
    return request._tm


def get_transaction(request):
    return request._tm.get()
