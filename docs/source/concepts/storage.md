# Storage

## What it is
Storage is the persistence layer backing Guillotina resources, typically through
PostgreSQL/Cockroach integrations and transaction management.

## Why it matters
Storage performance and correctness directly affect request latency, durability,
and consistency.

## How it works
- Resource changes are staged in transactions.
- The configured backend persists object state.
- Search/catalog layers index persisted data for query use-cases.

## Minimal example
```yaml
# config excerpt
storages:
  mydb:
    storage: "postgres"
```

## Common failures
- Incorrect backend configuration prevents startup.
- Slow queries and lock contention degrade API response times.

## Related pages
- {doc}`transactions`
- {doc}`catalog`
- {doc}`../developer/persistence`
