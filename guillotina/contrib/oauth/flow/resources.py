"""Extensible OAuth `resource` identifiers (RFC 8707 style) for this authorization server.

Resource resolvers are callables ``(request, container) -> Iterable[str]`` of
absolute resource URIs allowed in authorize/token requests.

Audience resolvers are callables ``(request, container) -> str | None``. They
allow protocol integrations to declare the exact audience required for the
current request without coupling the OAuth validator to protocol-specific paths.

The oauth contrib registers the container issuer URL by default. Other packages
(for example MCP) register additional URIs via :func:`register_oauth_resource_resolver`.
"""

from __future__ import annotations

from typing import Callable, FrozenSet, Iterable, List, Optional


ResourceResolver = Callable[..., Iterable[str]]
AudienceResolver = Callable[..., Optional[str]]

_resource_resolvers: List[ResourceResolver] = []
_audience_resolvers: List[AudienceResolver] = []
_default_registered = False


def register_oauth_resource_resolver(resolver: ResourceResolver) -> None:
    if resolver not in _resource_resolvers:
        _resource_resolvers.append(resolver)


def register_oauth_audience_resolver(resolver: AudienceResolver) -> None:
    if resolver not in _audience_resolvers:
        _audience_resolvers.append(resolver)


def _default_container_resolver(request, container):
    from guillotina.contrib.oauth.api.urls import container_url

    return {container_url(request, container)}


def ensure_default_oauth_resources_registered() -> None:
    global _default_registered
    if _default_registered:
        return
    register_oauth_resource_resolver(_default_container_resolver)
    _default_registered = True


def oauth_allowed_resources(request, container) -> FrozenSet[str]:
    from guillotina import app_settings as _apps

    ensure_default_oauth_resources_registered()
    applications = set(_apps.get("applications") or [])
    out: set = set()
    for resolver in _resource_resolvers:
        if (
            getattr(resolver, "_oauth_resource_source", None) == "mcp"
            and "guillotina.contrib.mcp" not in applications
        ):
            continue
        urls = resolver(request, container)
        if urls:
            out.update(urls)
    return frozenset(out)


def oauth_required_audience(request, container) -> str:
    from guillotina import app_settings as _apps
    from guillotina.contrib.oauth.api.urls import container_url

    applications = set(_apps.get("applications") or [])
    for resolver in _audience_resolvers:
        if (
            getattr(resolver, "_oauth_resource_source", None) == "mcp"
            and "guillotina.contrib.mcp" not in applications
        ):
            continue
        resource = resolver(request, container)
        if resource:
            return resource
    return container_url(request, container)
