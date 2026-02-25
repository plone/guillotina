# Request and Response

## What it is
Guillotina processes HTTP requests asynchronously and returns structured JSON
responses for content and services.

## Why it matters
Request/response conventions are the contract your clients, integrations, and
extensions rely on.

## How it works
- Request parsing resolves context and identity.
- Service or default handlers execute against the resolved context.
- Responses include JSON payloads with metadata fields like `@id`.

## Minimal example
```shell
curl -u root:root http://localhost:8080/db/container
```

## Common failures
- Missing auth headers cause unauthorized responses.
- Invalid payload schemas return validation errors.

## Related pages
- {doc}`traversal`
- {doc}`transactions`
- {doc}`../api/request`
- {doc}`../api/response`
