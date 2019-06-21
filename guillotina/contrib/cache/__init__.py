from guillotina import configure


CACHE_PREFIX = 'gcache2-'

app_settings = {
    'cache': {
        'driver': 'guillotina.contrib.redis',  # Empty to use memory
        'updates_channel': 'guillotina',  # Empty to not subscribe
        'memory_cache_size': 209715200,
        'strategy': 'basic',
        'ttl': 3600,
    },
    'load_utilities': {
        'guillotina.cache': {
            'provides': 'guillotina.interfaces.ICacheUtility',
            'factory': 'guillotina.contrib.cache.utility.CacheUtility',
            'settings': {}
        }
    }
}


def includeme(root, settings):
    configure.scan('guillotina.contrib.cache.api')
