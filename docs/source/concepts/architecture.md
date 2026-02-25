# Architecture

## What it is
Guillotina is an ASGI-native, AsyncIO-first framework with a hierarchical
content model and pluggable services.

## Why it matters
Architecture choices define scalability, extension points, and how API behavior
maps to stored content.

## How it works
- ASGI request handling drives async service execution.
- Content is organized under database/container/content paths.
- Configuration and component registration control behavior, permissions, and
  adapters.

## Minimal example
```python
from guillotina.factory import make_app

app = make_app(settings={"applications": ["myapp"]})
```

## Common failures
- Blocking I/O in custom code reduces concurrency.
- Misconfigured applications list prevents expected components from loading.

## Related pages
- {doc}`object-model`
- {doc}`request-response`
- {doc}`../developer/component-architecture`
