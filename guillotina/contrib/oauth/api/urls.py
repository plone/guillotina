from urllib.parse import urlparse

from guillotina import app_settings
from guillotina.interfaces import IContainer
from guillotina.utils import get_current_container, get_full_content_path, get_url
from guillotina.utils.misc import build_url


def container_url(request, container):
    issuer = app_settings.get("oauth", {}).get("issuer")
    if issuer:
        return issuer.rstrip("/")
    if not IContainer.providedBy(container):
        try:
            container = get_current_container()
        except (ValueError, AttributeError, RuntimeError, LookupError):
            pass
    if not IContainer.providedBy(container):
        raise RuntimeError("OAuth container URL requires a container context")
    path = get_full_content_path(container)
    if app_settings.get("oauth", {}).get("trust_proxy_headers", False):
        return get_url(request, path).rstrip("/")
    # Secure default: do not honor client-spoofable forwarding/virtualhost headers
    # (X-Forwarded-Proto, X-VirtualHost-*) when deriving the OAuth issuer. Only the
    # transport scheme and the Host header are used. For HTTPS deployments behind a
    # trusted reverse proxy set oauth.trust_proxy_headers=True, or pin oauth.issuer.
    return build_url(scheme=request.scheme, host=request.host, path=path, query="").rstrip("/")


def mcp_resource(request, container):
    return f"{container_url(request, container)}/@mcp/protocol"


def issuer_path(request, container):
    return urlparse(container_url(request, container)).path.lstrip("/")


def well_known_authorization_server_url(request, container):
    return (
        f"{request.scheme}://{request.host}/.well-known/oauth-authorization-server/"
        f"{issuer_path(request, container)}"
    )


def well_known_openid_configuration_url(request, container):
    return (
        f"{request.scheme}://{request.host}/.well-known/openid-configuration/"
        f"{issuer_path(request, container)}"
    )


def well_known_protected_resource_url(request, container):
    parsed = urlparse(mcp_resource(request, container))
    return f"{parsed.scheme}://{parsed.netloc}/.well-known/oauth-protected-resource/{parsed.path.lstrip('/')}"


def validate_resource(request, container, resources):
    from guillotina.contrib.oauth.api.request import normalize_list, oauth_error
    from guillotina.contrib.oauth.flow.resources import oauth_allowed_resources

    base = container_url(request, container)
    allowed = oauth_allowed_resources(request, container)
    if not resources:
        return [base]
    resources = normalize_list(resources)
    for resource in resources:
        if resource not in allowed:
            oauth_error("invalid_target", "resource is not allowed")
    return resources
