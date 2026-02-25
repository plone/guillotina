# Transactions

## What it is
Transactions group related persistence operations so writes are committed or
rolled back coherently.

## Why it matters
Transactional consistency protects data integrity under concurrency and failures.

## How it works
- Request handling opens a transaction context.
- Resource mutations are tracked during execution.
- On success, changes commit; on failure, changes rollback.

## Minimal example
```python
from guillotina.transactions import get_tm

tm = get_tm()
await tm.begin()
# mutate content
await tm.commit()
```

## Common failures
- Long-running transactions increase lock/contention risk.
- Exceptions without proper handling can leave partial in-memory state.

## Related pages
- {doc}`storage`
- {doc}`request-response`
- {doc}`../api/transactions`
