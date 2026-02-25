# Catalog

## What it is
The catalog provides indexed search capabilities over Guillotina content.

## Why it matters
Without indexing, content discovery and filtering are expensive and hard to
scale.

## How it works
- Content fields are indexed according to catalog configuration.
- Query endpoints use indexed metadata for fast retrieval.
- Reindex flows keep index state in sync with content changes.

## Minimal example
```shell
curl -u root:root http://localhost:8080/db/container/@search
```

## Common failures
- Missing index fields cause poor query relevance.
- Stale indexes produce incomplete or outdated search results.

## Related pages
- {doc}`storage`
- {doc}`traversal`
- {doc}`../rest/search`
