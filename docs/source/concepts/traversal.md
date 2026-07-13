# Traversal

## What it is

Traversal resolves an incoming URL to the object that a service will operate on.
Guillotina walks the path from application root to database, container, content,
and finally an optional service name such as `@search`.

## Where it appears

Traversal runs before service execution. During traversal Guillotina also sets
request-scoped task variables such as the active database, container,
transaction manager, and current transaction.

## Example path

```text
GET /db/docs/article-1/@sharing
```

This resolves `db`, then `docs`, then `article-1`, and dispatches the `@sharing`
service for that resolved context.

## Register a service

```python
from guillotina import configure
from guillotina.interfaces import IContainer


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.ViewContent",
    name="@summary",
)
async def summary(context, request):
    return {"id": context.id, "path": request.path}
```

## Extension points

- Register services for the interface that traversal should resolve.
- Use route-aware services only when path segments should not map directly to
  resource children.
- Keep permission declarations close to service registration so traversal and
  authorization remain understandable together.

## Common failures

- A missing path segment returns a traversal/not-found response before service
  code runs.
- Registering a service on the wrong context interface makes the URL resolve but
  the service remain unavailable.
- Assuming the request container is always the same as the resolved context is
  wrong for nested content.

## Related pages

- {doc}`object-model`
- {doc}`request-response`
- {doc}`task-vars`
- {doc}`../developer/router`
