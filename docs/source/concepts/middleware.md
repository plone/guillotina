# Middleware

## What it is
Middleware is request/response pipeline logic that wraps endpoint execution.

## Why it matters
It is the right place for cross-cutting behavior such as logging, tracing,
request metadata, and common guards.

## How it works
- Incoming request enters middleware chain.
- Each middleware can inspect/modify request or response.
- Control passes to the next middleware until endpoint execution completes.

## Minimal example
```python
async def middleware(app, handler):
    async def wrapped(request):
        response = await handler(request)
        return response
    return wrapped
```

## Common failures
- Blocking operations inside middleware affect every request.
- Unexpected mutation of request/response objects causes subtle regressions.

## Related pages
- {doc}`request-response`
- {doc}`security-model`
- {doc}`../developer/advanced`
