# Configuration

`guillotina` and its addons define a global configuration that is used.
All of these settings are configurable by providing a
JSON configuration file to the start script.

By default, the startup script looks for a `config.yaml` file. You can use a different
file by using the `-c` option for the script like this: `./bin/guillotina -c myconfig.yaml`.


## Databases

Guillotina uses PostgreSQL out-of-the-box.

To configure available databases, use the `databases` option. Configuration options
map 1-to-1 to database setup:

```yaml
---
databases:
  - db:
      storage: postgresql
      dsn:
        scheme: postgres
        dbname: guillotina
        user: postgres
        host: localhost
        password: ''
        port: 5432
      read_only: false
```

Currently supported database drivers are:

- `postgresql`
- `cockroach`


### Database configuration options

- `pool_size`: Size of connection pool. (defaults to `13`)
- `transaction_strategy`: Connection strategy to use. See `Transaction strategy`_ for details. (defaults to `resolve_readcommitted`)
- `conn_acquire_timeout`: How long to wait for connection to be freed up from pool. (defaults to `20`)
- `cache_strategy`: If you have something like guillotina_rediscache installed, you can configure here. (defaults to `dummy`)
- `objects_table_name`: Table name to store object data. (defaults to `objects`)
- `blobs_table_name`: Table name to store blob data. (defaults to `blobs`)


## Static files

```yaml
static:
  favicon.ico: static/favicon.ico
  static_files: module_name:static
```

These files will then be available on urls `/favicon.ico` and `/static_files`.


## JavaScript Applications

We can also serve JS apps from guillotina. These will allow routing on your
JS application without any extra configuration by returning the base directory
`index.html` for every sub directory in the url.

Once there is SSR support in Python, guillotina will integrate with it through
this as well.

```yaml
jsapps:
  app: path/to/app
```

## Root user password

```yaml
root_user:
  password: root
```

## CORS

```yaml
cors:
  allow_origin:
    - "*"
  allow_methods:
    - GET
    - POST
    - DELETE
    - HEAD
    - PATCH
    - PUT
  allow_headers:
    - "*"
  expose_headers:
    - "*"
  allow_credentials: true
  max_age: 3660
```

## Applications

To extend/override Guillotina, the `applications` configuration allows you to
specify which to enable.

```yaml
applications:
  - guillotina_elasticsearch
```


## Async utilities

```yaml
load_utilities:
  catalog:
    provides: guillotina.interfaces.ICatalogUtility
    factory: guillotina_elasticsearch.utility.ElasticSearchUtility
    settings: {}
```

## Middleware

`guillotina` is built on `aiohttp` which provides support for middleware.
You can provide an array of dotted names to use for your application.

```yaml
middlewares:
  - guillotina_myaddon.Middleware
```

## aiohttp settings

You can pass `aiohttp_settings` to configure the aiohttp server.


```yaml
aiohttp_settings:
  client_max_size: 20971520
```

## JWT Settings

If you want to enable JWT authentication, you'll need to configure the JWT
secret in Guillotina.

```yaml
jwt:
  secret: foobar
  algorithm: HS256
```


## Miscellaneous settings

- `port` (number): Port to bind to. _defaults to `8080`_
- `access_log_format` (string): Customize access log format for aiohttp. _defaults to `None`_
- `store_json` (boolean): Serialize object into json field in database. _defaults to `false`_
- `host` (string): Where to host the server. _defaults to `"0.0.0.0"`_
- `port` (number): Port to bind to. _defaults to `8080`_
- `conflict_retry_attempts` (number): Number of times to retry database conflict errors. _defaults to `3`_
- `cloud_storage` (string): Dotted path to cloud storage field type. _defaults to `"guillotina.interfaces.IDBFileField"`_


## Transaction strategy

Guillotina provides a few different modes to operate in to customize the level
of performance versus consistency. The setting used for this is `transaction_strategy`
which defaults to `resolve`.

Even though we have different transaction strategies that provide different voting
algorithms to decide if it's a safe write, all write operations STILL make sure that the
object committed matches the transaction it was retrieved with. If not,
a conflict error is detected and the request is retried. So even if you choose
the transaction strategy with no database transactions, there is still a level
of consistency so that you know you will only modify an object that is consistent
with the one retrieved from the database.

Example configuration:

```yaml
databases:
  - db:
      storage: postgresql
      transaction_strategy: resolve
      dsn:
        scheme: postgres
        dbname: guillotina
        user: postgres
        host: localhost
        password: ''
        port: 5432
```

Available options:

- `none`:
  No db transaction, no conflict resolution. Fastest but most dangerous mode.
  Use for importing data or if you need high performance and do not have multiple writers.
- `tidonly`:
  The same as `none` with no database transaction; however, we still use the database
  to issue us transaction ids for the data committed. Since no transaction is used,
  this is potentially just as safe as any of the other strategies just as long
  as you are not writing to multiple objects at the same time — in those cases,
  you might be in an inconsistent state on `tid` conflicts.
- `dbresolve`:
  Use db transaction but do not perform any voting when writing(no conflict resolution).
- `dbresolve_readcommitted`:
  Same as no vote; however, db transaction only started at commit phase. This
  should provide better performance; however, you'll need to consider the side
  affects of this for reading data.
- `simple`:
  Detect concurrent transactions and error if another transaction id is committed
  to the db ahead of the current transaction id. This is the safest mode to operate
  in but you might see conflict errors.
- `resolve`:
  Same as simple; however, it allows commits when conflicting transactions
  are writing to different objects.
- `resolve_readcommitted`:
  Same as resolve however, db transaction only started at commit phase. This
  should provide better performance; however, you'll need to consider that side
  affects of this for reading data.


Warning: not all storages are compatible with all transaction strategies.


## Connection class

The default asyncpg connection class has some overhead. Guillotina provides
a way to override it with a custom class or a provided lighter one:

```yaml
pg_connection_class: guillotina.db.storages.pg.LightweightConnection
```
