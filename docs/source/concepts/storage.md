# Storage

## What it is

Storage is the persistence layer behind Guillotina databases. Production systems
normally use `postgresql`; `cockroach`, `DUMMY`, and `DUMMY_FILE` are also
available for specific deployment or testing needs.

## Where it appears

Storage is configured under `databases`. The configuration key becomes the first
URL segment after the host, so a database named `db` is available at `/db`.

## Configure PostgreSQL

```yaml
databases:
  db:
    storage: postgresql
    dsn: postgresql://postgres@localhost:5432/guillotina
    pool_size: 40
```

## Extension points

- Configure multiple databases for separate URL roots.
- Use `storages` settings when exposing dynamic database creation through the
  storage APIs.
- Tune database options such as pool size, object table name, blob table name,
  and autovacuum behavior for production workloads.

## Common failures

- Using `postgres` instead of `postgresql` does not match Guillotina's storage
  backend name.
- A DSN without the database name is valid for `storages`, but not for a normal
  configured database.
- Slow queries, large transactions, and lock contention appear as API latency.
- Disabling autovacuum requires an external maintenance process.

## Related pages

- {doc}`transactions`
- {doc}`catalog`
- {doc}`../installation/configuration`
- {doc}`../developer/persistence`
