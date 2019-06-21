from guillotina.component import get_utility
from guillotina.tests import mocks
from guillotina.tests.utils import create_content
from guillotina.db.cache.cache import BasicCache
from guillotina.interfaces import ICacheUtility

import pytest

DEFAULT_SETTINGS = {
    'applications': [
        'guillotina',
        'guillotina.contrib.cache',
    ],
    'cache': {
        'updates_channel': None,
        'driver': None
    }
}

@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_cache_set(guillotina_main, loop):
    util = get_utility(ICacheUtility)
    assert util.initialized
    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set('bar', oid='foo')
    # but also in memory
    assert util._memory_cache.get('root-foo') == 'bar'
    # and api matches..
    assert await rcache.get(oid='foo') == 'bar'


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_cache_delete(guillotina_main, loop):
    util = get_utility(ICacheUtility)
    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set('bar', oid='foo')
    # make sure it is in redis
    assert util._memory_cache.get('root-foo') == 'bar'
    assert await rcache.get(oid='foo') == 'bar'

    # now delete
    await rcache.delete('root-foo')
    assert await rcache.get(oid='foo') is None


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_cache_clear(guillotina_main, loop):
    util = get_utility(ICacheUtility)
    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set('bar', oid='foo')
    assert util._memory_cache.get('root-foo') == 'bar'
    assert await rcache.get(oid='foo') == 'bar'

    await rcache.clear()
    assert await rcache.get(oid='foo') is None


@pytest.mark.app_settings(DEFAULT_SETTINGS)
async def test_invalidate_object(guillotina_main, loop):
    util = get_utility(ICacheUtility)
    trns = mocks.MockTransaction(mocks.MockTransactionManager())
    trns.added = trns.deleted = {}
    content = create_content()
    trns.modified = {content.__uuid__: content}
    rcache = BasicCache(trns)
    await rcache.clear()

    await rcache.set('foobar', oid=content.__uuid__)
    assert util._memory_cache.get('root-' + content.__uuid__) == 'foobar'
    assert await rcache.get(oid=content.__uuid__) == 'foobar'

    await rcache.close(invalidate=True)
    assert await rcache.get(oid=content.__uuid__) is None


