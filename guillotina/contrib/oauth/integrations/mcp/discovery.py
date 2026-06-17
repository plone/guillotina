"""MCP protected resource metadata provider (discovery phase)."""

from guillotina.contrib.oauth.flow.scopes import oauth_scopes_supported
from guillotina.contrib.oauth.integrations.mcp.identifiers import (
    _mcp_resource_url_from_path,
    mcp_resource_indicator,
)
from guillotina.contrib.oauth.utils.urls import container_issuer_url


def _mcp_protected_resource_provider(request, context, protected_path):
    resource = mcp_resource_indicator(request, context) if protected_path is None else None
    if resource is None:
        resource = _mcp_resource_url_from_path(request, context, protected_path)
    if resource is None:
        return None
    issuer = container_issuer_url(request, context)
    return {
        "resource": resource,
        "authorization_servers": [issuer],
        "scopes_supported": oauth_scopes_supported(),
    }
