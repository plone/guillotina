"""Resource indicator during the access phase (runtime JWT validation).

Checks the required resource indicator (derived from ``aud`` claim) for the
current request.
"""

from __future__ import annotations

from guillotina.contrib.oauth.indicators.registry import _required_resolvers
from guillotina.contrib.oauth.utils.urls import container_issuer_url


def required_resource_indicator(request, container) -> str:
    for resolver in _required_resolvers:
        indicator = resolver(request, container)
        if indicator:
            return indicator
    return container_issuer_url(request, container)
