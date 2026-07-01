# Security Model

## What it is

Guillotina uses context-aware authorization. Users and groups receive roles, roles
grant permissions, and services declare which permission is required for a
request to succeed.

## Where it appears

- Authentication identifies the active principal.
- Traversal resolves the object context.
- Service registration declares a permission.
- Security policy checks whether the principal has that permission on the
  resolved context.

## Use permissions on a service

```python
from guillotina import configure
from guillotina.interfaces import IContainer


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.ViewContent",
    name="@secure-summary",
)
async def secure_summary(context, request):
    return {"id": context.id}
```

## Inspect sharing

```shell
curl -u root:root http://localhost:8080/db/docs/@sharing
```

## Extension points

- Use permissions on every service that exposes protected data or mutation.
- Use local roles when authorization should vary by container or content path.
- Keep public endpoints explicit with the appropriate public permission.

## Common failures

- Assigning roles at the wrong level can expose too much content or deny valid
  access.
- Registering a service with a broad context and permissive permission can make
  it available in more places than intended.
- Assuming global roles override contextual checks leads to incorrect security
  expectations.
- Search results are also security-sensitive; catalog queries should not bypass
  context permissions.

## Related pages

- {doc}`object-model`
- {doc}`traversal`
- {doc}`catalog`
- {doc}`../developer/security`
