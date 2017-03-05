import logging


logger = logging.getLogger('guillotina')


async def commit(request):
    try:
        await request._tm.commit()
    except AttributeError:
        logger.warn('Could not locate transaction manager to commit')


async def abort(request):
    try:
        await request._tm.abort()
    except AttributeError:
        logger.warn('Could not locate transaction manager to abort')


def tm(request):
    """Return shared transaction manager (from request)

    This is used together with "with" syntax for wrapping mutating
    code into a request owned transaction.

    :param request: request owning the transaction

    Example::

        with tm(request) as txn:  # begin transaction txn

            # do something

        # transaction txn commits or raises ConflictError

    """
    return request._tm.get()
