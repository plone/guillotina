# Persistence

There are three kinds of objects that are considered on the system:


- Tree objects: objects are resources that implement `guillotina.interfaces.IResource`.
  This object has a `__name__` and a `__parent__` property that indicate the id
  on the tree and the link to the parent. By themselves they don't have access to
  their children, they need to interact with the transaction object to get them.
- Annotations: objects that are associated with tree objects. These can be
  any type of data. In Guillotina, the main source of annotation objects are
  behaviors.


## Saving objects

If you're manually modifying objects in services(or views) without using
the serialization adapters, you need to register the object to be saved
to the database. To do this, just use the `_p_register()` method.


```python
from guillotina import configure
@configure.service(
    method='PATCH', name='@dosomething')
async def matching_service(context, request):
    context.foobar = 'foobar'
    context._p_register()
```


## Transactions

Guillotina automatically manages transactions for you in services; however,
if you have long running services and need to flush data to the database,
you can manually manage transactions as well.

```python
from guillotina.transactions import get_tm

tm = get_tm()
await tm.commit()  # commit current transaction
await tm.begin()  # start new one
```

There is also an async context manager:

```python
from guillotina.transactions import managed_transaction

async with managed_transaction() as txn:
    # modify objects
```
