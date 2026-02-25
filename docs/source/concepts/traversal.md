# Traversal

## What it is
Traversal is the process that resolves URL paths into Guillotina context
objects.

## Why it matters
Correct traversal is required for service lookup, permission checks, and route
behavior.

## How it works
- The router parses incoming paths segment by segment.
- Each segment resolves to a resource in the object tree.
- Once context is resolved, service dispatch and security policy are applied.

## Minimal example
```text
GET /db/my-container/folder-a/item-1/@search
```
The path resolves to `item-1`, then the service endpoint is dispatched.

## Common failures
- Missing segments produce 404-style traversal errors.
- Wrong context assumptions in services break permission logic.

## Related pages
- {doc}`object-model`
- {doc}`request-response`
- {doc}`../developer/router`
