"""OAuth 2.0 Protected Resource Metadata (RFC 9728)."""

from guillotina.contrib.oauth.discovery.routing import register_well_known_handler
from guillotina.response import HTTPNotFound


_PROTECTED_RESOURCE_PROVIDERS = []


def register_protected_resource_provider(provider):
    _PROTECTED_RESOURCE_PROVIDERS.append(provider)


def reset_protected_resource_providers() -> None:
    _PROTECTED_RESOURCE_PROVIDERS.clear()


def _protected_resource_metadata(request, container):
    protected_path = getattr(request, "oauth_protected_resource_path", None)
    for provider in _PROTECTED_RESOURCE_PROVIDERS:
        metadata = provider(request, container, protected_path)
        if metadata is not None:
            return metadata
    raise HTTPNotFound(content={"reason": "Unknown protected resource"})


register_well_known_handler("oauth-protected-resource", _protected_resource_metadata)
