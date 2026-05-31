"""Best-effort, in-memory sliding-window rate limiter.

Used to throttle anonymous OAuth dynamic client registration (RFC 7591) so an
open registration endpoint cannot be trivially abused to flood the store.

Notes / limitations:
- State is per-process. Behind multiple workers each process keeps its own
  window; the effective global limit is ``limit * workers``. For stricter
  guarantees use a shared backend (e.g. Redis), but this provides a cheap and
  effective first line of defense without extra infrastructure.
- Keys are bounded to avoid unbounded memory growth from many distinct callers.
"""

import time
from collections import deque


_MAX_TRACKED_KEYS = 50000
_buckets: "dict[str, deque]" = {}


def reset_rate_limits():
    """Clear all tracked windows (used by tests)."""
    _buckets.clear()


def _prune_if_needed():
    if len(_buckets) <= _MAX_TRACKED_KEYS:
        return
    # Drop the oldest-tracked half. ``dict`` preserves insertion order, which is
    # a good enough approximation of staleness for eviction purposes.
    for key in list(_buckets.keys())[: len(_buckets) // 2]:
        _buckets.pop(key, None)


def rate_limit_exceeded(key, *, limit, window, now=None):
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
