# Task Variables

## What it is
Task variables are contextual values passed through execution flow to support
service behavior, async utilities, and request-scoped operations.

## Why it matters
They help avoid global mutable state and keep behavior deterministic per request
or task execution.

## How it works
- Variables are created in request/task context.
- Async flow propagates context-aware values.
- Services and utilities consume those values where needed.

## Minimal example
```python
# pseudo-code
context_vars["request_id"] = request.headers.get("X-Request-ID")
```

## Common failures
- Context leakage across async boundaries.
- Assuming task-local values are globally available.

## Related pages
- {doc}`transactions`
- {doc}`middleware`
- {doc}`../developer/async_utils`
