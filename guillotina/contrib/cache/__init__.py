from guillotina import configure


CACHE_PREFIX = "gcache2-"

app_settings = {
    "cache": {
        "driver": None,  # to use redis 'guillotina.contrib.redis', empty memory
        "updates_channel": None,  # to use pubsub invalidation you need a id for the channel
        "memory_cache_size": 209715200,
        "strategy": "basic",
        "ttl": 3600,
        "push": True,  # push out object data to fill other guillotina caches with changes
    },
    "load_utilities": {
        "guillotina_cache": {
            "provides": "guillotina.interfaces.ICacheUtility",
            "factory": "guillotina.contrib.cache.utility.CacheUtility",
            "settings": {},
        }
    },
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.cache.api")
    configure.scan("guillotina.contrib.cache.strategy")
