"""MCP resource indicator identification helpers."""

from urllib.parse import urlparse

from guillotina.contrib.oauth.utils.urls import container_issuer_url


def _mcp_resource_url_from_path(request, container, path):
    issuer = urlparse(container_issuer_url(request, container))
    target_path = "/" + str(path or "").strip("/")
    container_path = issuer.path.rstrip("/")
    if not target_path.endswith("/@mcp/protocol"):
        return None
    if target_path != f"{container_path}/@mcp/protocol" and not target_path.startswith(f"{container_path}/"):
        return None
    return f"{issuer.scheme}://{issuer.netloc}{target_path}"


def _mcp_resource_url_from_value(request, container, value):
    issuer = urlparse(container_issuer_url(request, container))
    parsed = urlparse(value)
    if parsed.scheme != issuer.scheme or parsed.netloc != issuer.netloc:
        return None
    if parsed.query or parsed.fragment:
        return None
    return _mcp_resource_url_from_path(request, container, parsed.path)


def mcp_resource_indicator(request, container):
    protected_path = getattr(request, "oauth_protected_resource_path", None)
    if protected_path:
        resource = _mcp_resource_url_from_path(request, container, protected_path)
        if resource:
            return resource
    request_path = str(getattr(request, "path", "") or "")
    if request_path.endswith("/@mcp/protocol"):
        resource = _mcp_resource_url_from_path(request, container, request_path)
        if resource:
            return resource
    return f"{container_issuer_url(request, container)}/@mcp/protocol"
