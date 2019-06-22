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

This option is not recomended as they are not invalidating the memory objects.

Its needed to add `aioredis` as a dependency on your project

### Configuration

```yaml
applications:
- guillotina.contrib.redis
- guillotina.contrib.cache
cache:
- driver: guillotina.contrib.redis
```

## In Storage Cache

This option is the recomended one for more than one process running guillotina on the same DB.

Its needed to add `aioredis` as a dependency on your project

### Configuration

```yaml
applications:
- guillotina.contrib.redis
- guillotina.contrib.pubsub
- guillotina.contrib.cache
cache:
- driver: guillotina.contrib.redis
- updates_channel: guillotina
```

