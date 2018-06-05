# AsyncIO Utilities

Guillotina comes with some amazing utilities to make working with
AsyncIO a bit easier.

Of those, Guillotina provides functions to run asychronous functions
in a queue or a pool.


For example, sending an email:

```python

from guillotina import configure
from guillotina.utils import execute


async def send_email(to_, from_, subject, body):
    pass


@configure.service(name='@myservice', method='GET',
                   permission='guillotina.AccessContent')
async def my_service(context, request):
    execute.in_pool(
        send_email, 'foo@bar', 'foo@bar', 'Hello!', 'Some body!').after_request()
    return {
        'foo': 'bar'
    }

```

This will execute the function `send_email` in an asynchronous pool after the request is finished.

The functions `execute.in_queue`, `execute.in_queue_with_func`, `execute.after_commit` and `execute.before_commit` are also available.

See the [full specification](../api/utils.html#module-guillotina.utils.execute).