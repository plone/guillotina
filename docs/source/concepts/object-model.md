# Object Model

## What it is
Guillotina models content as a tree rooted at application/database/container
objects, then user-defined content beneath them.

## Why it matters
URL paths, security inheritance, and traversal behavior all depend on this
hierarchy.

## How it works
- `/` is the application root.
- `/(db)` selects a configured database.
- `/(db)/(container)` scopes content and permissions.
- Child resources live under containers and inherit contextual behavior.

## Minimal example
```shell
curl -u root:root -X POST http://localhost:8080/db -d '{"@type":"Container","id":"docs"}'
curl -u root:root http://localhost:8080/db/docs
```

## Common failures
- Creating content in the wrong container causes security and query confusion.
- Assuming flat models breaks inheritance expectations.

## Related pages
- {doc}`traversal`
- {doc}`security-model`
- {doc}`../developer/narrative`
