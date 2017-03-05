
async def commit(request):
    await request._tm.commit()


async def abort(request):
    await request._tm.abort()


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
