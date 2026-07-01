# Task Variables

## What it is

Task variables are Python `contextvars.ContextVar` values used by Guillotina to
carry request-scoped state through async execution. They avoid process-wide
globals while still making the active request, transaction, database, container,
and user available to internals that need them.

## Where it appears

- `task_vars.request` is set when Guillotina creates the request.
- `task_vars.db`, `task_vars.container`, `task_vars.tm`, and `task_vars.txn` are
  set during traversal and transaction handling.
- `task_vars.authenticated_user` is set by authentication utilities.
- Conflict retry cleanup resets task variables before re-running request logic.

## Read request context

```python
from guillotina import task_vars
from guillotina.transactions import get_transaction
from guillotina.utils.auth import get_authenticated_user


request = task_vars.request.get()
container = task_vars.container.get()
txn = get_transaction()
user = get_authenticated_user()
```

## Extension points

- Use task variables for read access to the current Guillotina execution context.
- Prefer explicit function parameters in application code when possible.
- Let Guillotina set core task variables; avoid setting them manually except in
  framework utilities, tests, or controlled background execution.

## Common failures

- Reading a task variable outside a request can return `None`.
- Manually setting task variables without restoring them can leak context into
  later async work.
- Assuming task variables are process-global breaks under concurrent ASGI
  requests.

## Related pages

- {doc}`transactions`
- {doc}`middleware`
- {doc}`request-response`
- {doc}`../developer/async_utils`
