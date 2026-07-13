# Transactions

## What it is

Transactions group persistence work so Guillotina can commit successful changes
or abort failed changes coherently. The active transaction and transaction
manager are stored in task variables during request handling.

## Where it appears

- Traversal selects the database and transaction manager.
- Mutating services register changed objects with the active transaction.
- Successful request work commits; errors abort.
- Conflict errors can trigger request retries according to application settings.

## Use an explicit transaction

```python
from guillotina.transactions import transaction


async with transaction() as txn:
    obj.title = "Updated title"
    txn.register(obj)
```

## Extension points

- Use `guillotina.transactions.get_transaction()` to inspect the active
  transaction in code that already runs inside a request.
- Use `async with transaction()` for explicit transaction scopes in code that
  already runs inside a request (it reuses the request transaction manager).
- In background tasks with no active request, pass an explicit database, for
  example `async with transaction(db=db)`, so a transaction manager is available.
- Use `read_only=True` for scopes that should not write.

## Common failures

- Long-running transactions increase lock contention.
- Mutating objects outside an active transaction loses persistence guarantees.
- Swallowing exceptions can accidentally commit state that should have aborted.
- Running blocking work inside a transaction holds database resources longer than
  necessary.

## Related pages

- {doc}`storage`
- {doc}`request-response`
- {doc}`task-vars`
- {doc}`../api/transactions`
