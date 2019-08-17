_bytes = b"x" * 3


def test_lrusized_acts_like_a_dict():
    from guillotina.contrib.cache.lru import LRU

    m = LRU(1024)
    m.set("a", _bytes, 3)
    assert m["a"] == _bytes
    assert "a" in m
    assert m.get("a") == _bytes
    assert m.get_memory() == 3
    del m["a"]
    assert len(m.keys()) == 0
    assert m.get_memory() == 0


def test_clean_till_it_has_enought_space():
    from guillotina.contrib.cache.lru import LRU

    m = LRU(19)
    for k in range(20):
        m.set(k, k, 1)

    m.set("a", 1, 1)
    assert 1 not in m.keys()
    r = m[2]
    assert r == 2
    m.set("b", 1, 1)
    assert 2 in m.keys()
    assert 3 not in m.keys()
    m.set("b", 1, 10)
    assert len(m.keys()) == 10
    assert 2 in m.keys()

    assert m.get_memory() == 19
    del m["b"]
    assert m.get_memory() == 9
    assert len(m.keys()) == 9

    # we should cleanup 12 keys
    assert m.get_stats() == (1, 0, 12)


def test_setting_a_bigger_value_than_cache_doesnt_brake():
    from guillotina.contrib.cache.lru import LRU

    m = LRU(1)
    m.set("a", "v", 100)
    assert "a" not in m.keys()


def test_cache_stats_are_hit():
    from guillotina.contrib.cache.lru import LRU

    m = LRU(1)
    try:
        m["a"]
    except KeyError:
        pass
    assert m.get_stats() == (0, 1, 0)

    m.set("a", 1, 1)
    assert m["a"] == 1
    assert m.get_stats() == (1, 1, 0)


def test_cache_clear_resets_memory():
    from guillotina.contrib.cache.lru import LRU

    m = LRU(2)
    m.set("a", 1, 1)
    assert m.get_memory() == 1
    m.clear()
    assert m.get_memory() == 0
    assert "a" not in m.keys()
