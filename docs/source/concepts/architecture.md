# Architecture

## What it is

Guillotina is an ASGI-native application server for hierarchical JSON resources.
Requests enter an ASGI middleware stack, resolve a database/container/content
context, execute a registered service, and persist changes through an async
transaction manager.

## Where it appears

- `guillotina.factory.make_app()` builds the application from settings.
- `guillotina.asgi` builds the ASGI middleware stack and request handler.
- Configured `applications` load content types, services, adapters, utilities,
  permissions, and subscribers.
- Configured `databases` expose top-level URL segments such as `/db`.

## Minimal example

```python
from guillotina.factory import make_app

app = make_app(
    settings={
        "applications": ["myapp"],
        "root_user": {"password": "root"},
        "databases": {
            "db": {
                "storage": "DUMMY_FILE",
                "filename": "dummy_file.db",
            }
        },
    }
)
```

## Extension points

- Add content types with `@configure.contenttype`.
- Add REST endpoints with `@configure.service`.
- Add cross-cutting ASGI behavior with `settings["middlewares"]`.
- Add persistence, security, serialization, or event behavior through Guillotina
  components.

## Common failures

- Blocking I/O inside services or middleware reduces ASGI concurrency.
- Missing application entries prevent decorators from being loaded.
- Registering services on the wrong context interface makes traversal succeed
  but service lookup fail.
- Treating the object tree as flat breaks permission and traversal assumptions.

## Related pages

- {doc}`object-model`
- {doc}`request-response`
- {doc}`middleware`
- {doc}`../developer/component-architecture`
