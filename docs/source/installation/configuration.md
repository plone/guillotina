# Configuration

`guillotina` and it's addon define global configuration that is used throughout
the `guillotina`. All of these settings are configurable by providing a
JSON configuration file to the start script.

By default, the startup script looks for a `config.json` file. You can use a different
file by using the `-c` option for the script script like this `./bin/guillotina -c myconfig.json`.


## Databases

Guillotina uses postgresql OOTB.

To configure available databases, use the `databases` option. Configuration options
map 1-to-1 to database setup:

```json
{
  "databases": [{
    "db": {
      "storage": "postgresql",
      "dsn": {
        "scheme": "postgres",
        "dbname": "guillotina",
        "user": "postgres",
        "host": "localhost",
        "password": "",
        "port": 5432
      },
      "read_only": false
    }
  }]
}
```

Currently supported database drivers are:

- `postgresql`
- `cockroach`


### Cockroach

Both postgres and cockroach have configurations that are identical; however,
Cockroach has an additional `isolation_level` configuration which defaults to `snapshot`. See
https://www.cockroachlabs.com/docs/transactions.html

It is recommended that you use the `lock` transaction strategy with Cockroach
which requires etcd.


## Static files

```json
{
  "static": [
    {"favicon.ico": "static/favicon.ico"},
    {"static_files": "module_name:static"}
  ]
}
```

These files will then be available on urls `/favicon.ico` and `/static_files`.


## Server port

```json
{
  "port": 8080
}
```

## Server host

```json
{
  "host": "0.0.0.0"
}
```

## Root user password

```json
{
  "root_user": {
    "password": "root"
  }
}
```

## CORS

```json
{
  "cors": {
    "allow_origin": ["*"],
    "allow_methods": ["GET", "POST", "DELETE", "HEAD", "PATCH"],
    "allow_headers": ["*"],
    "expose_headers": ["*"],
    "allow_credentials": true,
    "max_age": 3660
  }
}
```

## Async utilities

```json
{
  "utilities": [{
    "provides": "guillotina.interfaces.ICatalogUtility",
    "factory": "guillotina_elasticsearch.utility.ElasticSearchUtility",
    "settings": {}
  }]
}
```

## Middleware

`guillotina` is built on aiohttp which provides support for middleware.
You can provide an array of dotted names to middle ware to use for your application.

```json
{
  "middlewares": [
    "guillotina_myaddon.Middleware"
  ]
}
```


## aiohttp settings

You can pass in aiohttp_settings to configure the aiohttp server.


```json
{
  "aiohttp_settings": {
    "client_max_size": 20971520
  }
}
```

## transaction strategy

Guillotina provides a few different modes to operate in to customize the level
of performance vs consistency. The setting used for this is `transaction_strategy`
which defaults to `resolve`.

Even though we have different transaction strategies that provide different voting
algorithms to decide if it's a safe write, all writes STILL make sure that the
object committed to matches the transaction it was retrieved with. If not,
a conflict error is detected and the request is retried. So even if you choose
the transaction strategy with no database transactions, there is still a level
of consistency in that you know you aren't modifying an object that isn't consistent
with when it was retrieved from the database.

Example configuration:

```json
{
  "databases": [{
		"db": {
			"storage": "postgresql",
			"transaction_strategy": "resolve",
      "dsn": {
        "scheme": "postgres",
        "dbname": "guillotina",
        "user": "postgres",
        "host": "localhost",
        "password": "",
        "port": 5432
      }
		}
	}]
}
```

Available options:

- `none`:
  No db transaction, no conflict resolution. Fastest but most dangerous mode.
  Use for importing data or if you need high performance and do not have multiple writers.
- `tidonly`:
  The same as `none` with no database transaction; however, we still use the database
  to issue us transaction ids for the data committed. Since no transaction is used,
  this is potentially just as safe as any of the other strategies just as long
  as you are not writing to multiple objects at the same time--in those cases,
  you might be in an inconsistent state on tid conflicts.
- `novote`:
  Use db transaction but do not perform any voting when writing.
- `simple`:
  Detect concurrent transactions and error if another transaction id is committed
  to the db ahead of the current transaction id. This is the safest mode to operate
  in but you might see conflict errors.
- `resolve`:
  Same as simple; however, it allows commits when conflicting transactions
  are writing to different objects.
- `lock`:
  As safe as the `simple` mode with potential performance impact since every
  object is locked when a known write will be applied to it.
  While it is locked, no other writers can access the object.
  Requires etcd installation.


Warning: not all storages are compatible with all transaction strategies.


## lock transaction strategy

Requires installation and configuration of etcd to lock content for writes.
See https://pypi.python.org/pypi/aio_etcd for etcd configuration options

```json
{
  "databases": [{
		"db": {
			"storage": "postgresql",
			"transaction_strategy": "lock",
      "dsn": {
        "scheme": "postgres",
        "dbname": "guillotina",
        "user": "postgres",
        "host": "localhost",
        "password": "",
        "port": 5432
      },
      "etcd": {
				"host": "127.0.0.1",
	      "port": 2379,
	      "protocol": "http",
	      "read_timeout": 2,
	      "allow_redirect": true,
	      "allow_reconnect": false,
				"base_key": "guillotina-",
				"read_timeout": 3,
				"acquire_timeout": 10
			}
		}
	}]
}
```


Another note: why are there so many choices? Well, this is all somewhat experimental
right now. We're trying to test the best scenarios of usage for different
databases and environments. We might eventually pare this down.
