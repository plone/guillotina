from guillotina import app_settings
from guillotina.contrib.cache.lru import LRU
from typing import Optional


try:
    import prometheus_client

    MEMORY_OPS = prometheus_client.Counter(
        "guillotina_cache_memory_ops_total",
        "Total count of ops by type of operation and the error if there was.",
        labelnames=["type", "result"],
    )

    def record_memory_op(type: str, result: str) -> None:
        MEMORY_OPS.labels(type=type, result=result).inc()


except ImportError:

    def record_memory_op(type: str, result: str) -> None:
        ...


_lru: Optional[LRU] = None


def _evicted(key, value):
    record_memory_op("evicted", "none")


def get_memory_cache() -> LRU:
    global _lru
    if _lru is None:
        settings = app_settings.get("cache", {"memory_cache_size": 209715200})
        _lru = LRU(settings["memory_cache_size"], callback=_evicted)
    return _lru
