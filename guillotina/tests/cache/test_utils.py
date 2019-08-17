from guillotina.contrib.cache.utility import CacheUtility


async def test_get_size_of_item():
    rcache = CacheUtility()
    from guillotina.contrib.cache.utility import _default_size
    import sys

    assert rcache.get_size(dict(a=1)) == _default_size
    assert rcache.get_size(1) == sys.getsizeof(1)
    assert rcache.get_size(dict(state=b"x" * 10)) == 10

    item = ["x" * 10, "x" * 10, "x" * 10]

    assert rcache.get_size(item) == sys.getsizeof("x" * 10) * 3
