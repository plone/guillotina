"""Best-effort sliding-window rate limiter.

Used to throttle anonymous OAuth dynamic client registration (RFC 7591) so an
open registration endpoint cannot be trivially abused to flood the store.

When Redis is configured via ``guillotina.contrib.redis`` this module stores
windows in Redis so limits are shared across workers. Without Redis it falls back
to a bounded in-memory store, which is still useful for development and simple
single-process deployments.
"""

import logging
import time
from collections import deque
from json import dumps, loads

from guillotina import app_settings


_MAX_TRACKED_KEYS = 50000
_buckets: "dict[str, deque]" = {}
logger = logging.getLogger("guillotina.contrib.oauth")

_redis_driver = None
_redis_unavailable = False
_REDIS_PREFIX = "oauth-rate-limit:v1"


def reset_rate_limits():
    """Clear all tracked windows (used by tests)."""
    global _redis_unavailable
    _redis_unavailable = False
    _buckets.clear()


def _prune_if_needed():
    if len(_buckets) <= _MAX_TRACKED_KEYS:
        return
    # Drop the oldest-tracked half. ``dict`` preserves insertion order, which is
    # a good enough approximation of staleness for eviction purposes.
    for key in list(_buckets.keys())[: len(_buckets) // 2]:
        _buckets.pop(key, None)


def _memory_rate_limit_exceeded(key, *, limit, window, now=None):
    """Register a hit for ``key`` and report whether it exceeds the window limit.

    ``limit <= 0`` disables the limiter (always allowed). When the call would
    exceed ``limit`` events within ``window`` seconds it returns ``True`` and
    does **not** record the hit, so a blocked caller cannot extend its own
    window indefinitely.
    """
    if not limit or limit <= 0:
        return False
    now = time.monotonic() if now is None else now
    cutoff = now - window
    bucket = _buckets.get(key)
    if bucket is None:
        bucket = deque()
        _buckets[key] = bucket
        _prune_if_needed()
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False


def _memory_rate_limit_check(key, *, limit, window, now=None):
    """Report whether ``key`` is already at/over the window limit without recording a hit.

    Useful to throttle expensive operations (such as password verification) by
    counting only failures: check first with this function, then record an
    actual failure with :func:`rate_limit_exceeded`.
    """
    if not limit or limit <= 0:
        return False
    now = time.monotonic() if now is None else now
    cutoff = now - window
    bucket = _buckets.get(key)
    if bucket is None:
        return False
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()
    return len(bucket) >= limit


def _redis_enabled():
    return "guillotina.contrib.redis" in set(app_settings.get("applications") or []) and bool(
        app_settings.get("redis")
    )


async def _get_redis_driver():
    global _redis_driver, _redis_unavailable
    if _redis_unavailable or not _redis_enabled():
        return None
    try:
        from guillotina.contrib.redis import get_driver

        _redis_driver = await get_driver()
        return _redis_driver
    except Exception:
        _redis_unavailable = True
        logger.warning(
            "OAuth rate limiter falling back to in-memory storage; Redis unavailable", exc_info=True
        )
        return None


def _redis_key(key):
    return f"{_REDIS_PREFIX}:{key}"


def _decode_redis_bucket(raw):
    if not raw:
        return []
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        data = loads(raw)
    except Exception:
        return []
    return [float(item) for item in data if isinstance(item, (int, float))]


async def _redis_bucket(driver, redis_key, *, window, now):
    cutoff = now - window
    bucket = _decode_redis_bucket(await driver.get(redis_key))
    return [item for item in bucket if item > cutoff]


async def _save_redis_bucket(driver, redis_key, bucket, *, window):
    await driver.set(redis_key, dumps(bucket), expire=max(int(window) + 1, 1))


async def _redis_rate_limit_exceeded(driver, key, *, limit, window, now=None):
    now = time.time() if now is None else now
    redis_key = _redis_key(key)
    bucket = await _redis_bucket(driver, redis_key, window=window, now=now)
    if len(bucket) >= limit:
        await _save_redis_bucket(driver, redis_key, bucket, window=window)
        return True
    bucket.append(now)
    await _save_redis_bucket(driver, redis_key, bucket, window=window)
    return False


async def _redis_rate_limit_check(driver, key, *, limit, window, now=None):
    now = time.time() if now is None else now
    redis_key = _redis_key(key)
    bucket = await _redis_bucket(driver, redis_key, window=window, now=now)
    await _save_redis_bucket(driver, redis_key, bucket, window=window)
    return len(bucket) >= limit


async def rate_limit_exceeded(key, *, limit, window, now=None):
    """Register a hit for ``key`` and report whether it exceeds the window limit.

    ``limit <= 0`` disables the limiter. When the call would exceed ``limit``
    events within ``window`` seconds it returns ``True`` and does not record the
    hit, so a blocked caller cannot extend its own window indefinitely.
    """
    if not limit or limit <= 0:
        return False
    driver = await _get_redis_driver()
    if driver is not None:
        try:
            return await _redis_rate_limit_exceeded(driver, key, limit=limit, window=window, now=now)
        except Exception:
            logger.warning("OAuth Redis rate limit check failed; using in-memory fallback", exc_info=True)
    return _memory_rate_limit_exceeded(key, limit=limit, window=window, now=now)


async def rate_limit_check(key, *, limit, window, now=None):
    """Report whether ``key`` is already at/over the window limit without recording a hit."""
    if not limit or limit <= 0:
        return False
    driver = await _get_redis_driver()
    if driver is not None:
        try:
            return await _redis_rate_limit_check(driver, key, limit=limit, window=window, now=now)
        except Exception:
            logger.warning("OAuth Redis rate limit check failed; using in-memory fallback", exc_info=True)
    return _memory_rate_limit_check(key, limit=limit, window=window, now=now)
