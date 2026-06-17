"""Extensible OAuth resource indicator registries (RFC 8707).

Resource indicator resolvers are callables ``(request, container) -> Iterable[str]``
of absolute resource URIs allowed in authorize/token requests.

Required indicator resolvers are callables ``(request, container) -> str | None``.
They allow protocol integrations to declare the exact resource indicator required
for the current request without coupling the OAuth validator to protocol-specific paths.

The oauth contrib registers the container issuer URL by default. Other packages
(for example MCP) register additional URIs from their own integration package,
typically loaded only when that addon is enabled.
"""

from __future__ import annotations

from typing import Callable, Iterable, List, Optional

from guillotina.contrib.oauth.utils.urls import container_issuer_url


ResourceResolver = Callable[..., Iterable[str]]
AudienceResolver = Callable[..., Optional[str]]

_allowed_resolvers: List[ResourceResolver] = []
_required_resolvers: List[AudienceResolver] = []
_default_registered = False


def register_allowed_indicator_resolver(resolver: ResourceResolver) -> None:
    if resolver not in _allowed_resolvers:
        _allowed_resolvers.append(resolver)


def register_required_indicator_resolver(resolver: AudienceResolver) -> None:
    if resolver not in _required_resolvers:
        _required_resolvers.append(resolver)


def _default_container_resolver(request, container):
    return {container_issuer_url(request, container)}


def ensure_default_resource_indicators_registered() -> None:
    global _default_registered
    if _default_registered:
        return
    register_allowed_indicator_resolver(_default_container_resolver)
    _default_registered = True


def reset_indicator_registries() -> None:
    global _default_registered
    _allowed_resolvers.clear()
    _required_resolvers.clear()
    _default_registered = False
