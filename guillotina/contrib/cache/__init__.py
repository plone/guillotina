from guillotina import configure


CACHE_PREFIX = 'gcache2-'

app_settings = {
    'cache': {
        'driver': '',  # to use redis 'guillotina.contrib.redis'
        'updates_channel': '',  # to use pubsub invalidation you need a id for the channel
        'memory_cache_size': 209715200,
        'strategy': 'basic',
        'ttl': 3600,
    },
    'load_utilities': {
        'guillotina_cache': {
            'provides': 'guillotina.interfaces.ICacheUtility',
            'factory': 'guillotina.contrib.cache.utility.CacheUtility',
            'settings': {}
        }
    }
}


def includeme(root, settings):
    configure.scan('guillotina.contrib.cache.api')
