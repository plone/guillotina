"""Resource indicators during the grant phase (authorize/token endpoints).

Validates the ``resource=`` parameter (RFC 8707) against registered allowed
indicator resolvers.
"""

from __future__ import annotations

from typing import FrozenSet

from guillotina.contrib.oauth.indicators.registry import (
    _allowed_resolvers,
    ensure_default_resource_indicators_registered,
)
from guillotina.contrib.oauth.utils.urls import container_issuer_url


def allowed_resource_indicators(request, container) -> FrozenSet[str]:
    ensure_default_resource_indicators_registered()
    out: set = set()
    for resolver in _allowed_resolvers:
        urls = resolver(request, container)
        if urls:
            out.update(urls)
    return frozenset(out)


def validate_resource_indicator(request, container, resource_indicators):
    from guillotina.contrib.oauth.utils.errors import raise_oauth_error
    from guillotina.contrib.oauth.utils.request import normalize_list

    base = container_issuer_url(request, container)
    allowed = allowed_resource_indicators(request, container)
    if not resource_indicators:
        return [base]
    resource_indicators = normalize_list(resource_indicators)
    for indicator in resource_indicators:
        if indicator not in allowed:
            raise_oauth_error("invalid_target", "resource is not allowed")
    return resource_indicators
