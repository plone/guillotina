# Cache

`guillotina` provides out of the box cache configuration, it support in-memory and network cache with redis.

By default it does not provide any cache, if you want to use it you need to add different configurations:


## In Memory Cache

This option is recomendable when you have only one guillotina process running on the same DB.


### Configuration

```yaml
applications:
- guillotina.contrib.cache
```

## In Storage Cache (No invalidations)

This option is not recommended as they are not invalidating the memory objects.

Its needed to add `redis` as a dependency on your project

### Configuration

```yaml
applications:
- guillotina.contrib.redis
- guillotina.contrib.cache
cache:
  driver: guillotina.contrib.redis
```

## Redis Storage Cache

This option is the recommended one for more than one process running guillotina on the same DB.

Its needed to add `redis` as a dependency on your project

### Configuration

```yaml
applications:
- guillotina.contrib.redis
- guillotina.contrib.pubsub
- guillotina.contrib.cache
cache:
  driver: guillotina.contrib.redis
  updates_channel: guillotina
```


### In-memory with redis invalidations

Object invalidations are coordinated across Guillotina instances; however, pushing
object data into and out of redis can be heavy on redis. Sometimes, an in-memory
cache configuration but using redis only for pubsub invalidations provides the
best performance.

```yaml
applications:
- guillotina.contrib.redis
- guillotina.contrib.pubsub
- guillotina.contrib.cache
cache:
  driver:
  updates_channel: guillotina
  push: false
-
```


## Memcached Storage Cache

The Memcached driver (`guillotina.contrib.memcached`) is to be used as
an alternative to Redis for a distributed cache for guillotina
objects.

The main advantage of [memcached](https://memcached.org/) is that
server instances are multi-threaded (in contrast to Redis instances,
that are single-threaded), so they scale up linearly on the number of
CPUs.

The `emcache` library is a required dependency.


### Configuration

```yaml
applications:
- guillotina.contrib.memcached
- guillotina.contrib.pubsub
- guillotina.contrib.cache
cache:
  driver: guillotina.contrib.memcached
memcached:
  hosts:
  - memcached.host1:11211
  - memcached.host2:11211
  timeout: 0.1
  max_connections: 4
  min_connections: 2
  purge_unused_connections_after: null
  purge_unhealthy_nodes: true
```


### Invalidations

Currently, cache invalidations are not supported by the memcached
driver. However, it is compatible with invalidations through redis.

```yaml
applications:
- guillotina.contrib.redis
- guillotina.contrib.memcached
- guillotina.contrib.pubsub
- guillotina.contrib.cache
cache:
  driver: guillotina.contrib.memcached
  updates_channel: guillotina
  push: false
```
