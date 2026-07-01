# Middleware

## What it is

Middleware is ASGI-compatible request/response code that wraps Guillotina's core
request handler. It is useful for cross-cutting behavior such as tracing,
metrics, headers, and request guards.

## Where it appears

Guillotina builds the middleware stack from `settings["middlewares"]`. Each
configured dotted name is resolved to a class, instantiated with the next ASGI
app, and called with `(scope, receive, send)`.

## Write ASGI middleware

```python
class TimingMiddleware:
    def __init__(self, app):
        self.next_app = app

    async def __call__(self, scope, receive, send):
        response = await self.next_app(scope, receive, send)
        response.headers["X-Middleware"] = "timing"
        return response
```

Unlike plain ASGI apps, Guillotina middlewares return the response object.
Guillotina's outermost handler prepares and sends that response after the chain
returns, so mutating `response.headers` before returning takes effect.

## Configure middleware

```yaml
middlewares:
  - myapp.middleware.TimingMiddleware
```

## Extension points

- Read request metadata from the ASGI `scope` before Guillotina creates the
  request object.
- Add response headers after calling `self.next_app`.
- Use middleware for behavior that applies to many services.

## Common failures

- Blocking work in middleware slows every request.
- Forgetting to call the next app prevents Guillotina from handling the request.
- Mutating shared state in middleware can leak data between concurrent requests.
- Using an aiohttp-style middleware signature will not match Guillotina's ASGI
  middleware shape.

## Related pages

- {doc}`request-response`
- {doc}`task-vars`
- {doc}`security-model`
- {doc}`../developer/advanced`
