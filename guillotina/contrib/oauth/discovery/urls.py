"""Well-known URL construction helpers."""

from urllib.parse import urlparse

from guillotina.contrib.oauth.indicators.access import required_resource_indicator


def well_known_protected_resource_url(request, container):
    parsed = urlparse(required_resource_indicator(request, container))
    return f"{parsed.scheme}://{parsed.netloc}/.well-known/oauth-protected-resource/{parsed.path.lstrip('/')}"
