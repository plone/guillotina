# Request and Response

## What it is

Guillotina turns an ASGI HTTP scope into a `Request`, resolves context, executes
a service or default handler, and renders a `Response`. User-facing APIs are JSON
by default and commonly include metadata fields such as `@id` and `@type`.

## Where it appears

- Middleware receives the ASGI `scope`, `receive`, and `send` callables.
- `Request.factory()` creates the Guillotina request object.
- The router resolves the request to a handler.
- Returned dictionaries are rendered into HTTP responses.

## Minimal request

```shell
curl -u root:root http://localhost:8080/db/docs
```

## Minimal service response

```python
from guillotina import configure
from guillotina.interfaces import IContainer


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.ViewContent",
    name="@health",
)
async def health(context, request):
    return {"ok": True, "container": context.id}
```

## Extension points

- Services receive `(context, request)` and can return serializable data.
- Renderers and serializers customize how Python objects become responses.
- Exceptions implementing Guillotina's error response interfaces are rendered as
  structured error payloads.

## Common failures

- Missing or invalid credentials produce an authorization error before service
  logic completes.
- Invalid JSON or schema values produce validation errors.
- Returning non-serializable objects from services fails during rendering.

## Related pages

- {doc}`traversal`
- {doc}`transactions`
- {doc}`../developer/services`
- {doc}`../api/request`
- {doc}`../api/response`
