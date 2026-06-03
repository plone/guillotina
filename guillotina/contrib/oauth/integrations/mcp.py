from urllib.parse import urlparse

from zope.interface import implementer

from guillotina import app_settings, configure
from guillotina.contrib.mcp.interfaces import IMCPAuthPolicy
from guillotina.contrib.oauth.api.request import normalize_list
from guillotina.contrib.oauth.api.services import register_well_known_handler
from guillotina.contrib.oauth.api.urls import container_url, well_known_protected_resource_url
from guillotina.contrib.oauth.flow.resources import (
    register_oauth_audience_resolver,
    register_oauth_resource_resolver,
)
from guillotina.contrib.oauth.flow.scopes import OAUTH_DEFAULT_SCOPE, oauth_scopes_supported


def _mcp_resource_url_from_path(request, container, path):
    issuer = urlparse(container_url(request, container))
    target_path = "/" + str(path or "").strip("/")
    container_path = issuer.path.rstrip("/")
    if not target_path.endswith("/@mcp/protocol"):
        return None
    if target_path != f"{container_path}/@mcp/protocol" and not target_path.startswith(f"{container_path}/"):
        return None
    return f"{issuer.scheme}://{issuer.netloc}{target_path}"


def _mcp_resource_url_from_value(request, container, value):
    issuer = urlparse(container_url(request, container))
    parsed = urlparse(value)
    if parsed.scheme != issuer.scheme or parsed.netloc != issuer.netloc:
        return None
    if parsed.query or parsed.fragment:
        return None
    return _mcp_resource_url_from_path(request, container, parsed.path)


def mcp_resource(request, container):
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
    return f"{container_url(request, container)}/@mcp/protocol"


def _mcp_protocol_resource_resolver(request, container):
    resources = {f"{container_url(request, container)}/@mcp/protocol"}
    params = getattr(request, "oauth_request_params", {}) or {}
    for value in normalize_list(params.get("resource")):
        resource = _mcp_resource_url_from_value(request, container, value)
        if resource:
            resources.add(resource)
    return resources


def _mcp_protocol_audience_resolver(request, container):
    if str(getattr(request, "path", "") or "").endswith("/@mcp/protocol"):
        return mcp_resource(request, container)


setattr(_mcp_protocol_resource_resolver, "_oauth_resource_source", "mcp")
setattr(_mcp_protocol_audience_resolver, "_oauth_resource_source", "mcp")
register_oauth_resource_resolver(_mcp_protocol_resource_resolver)
register_oauth_audience_resolver(_mcp_protocol_audience_resolver)


def _protected_resource_metadata(request, context):
    issuer = container_url(request, context)
    return {
        "resource": mcp_resource(request, context),
        "authorization_servers": [issuer],
        "scopes_supported": oauth_scopes_supported(),
    }


register_well_known_handler("oauth-protected-resource", _protected_resource_metadata)


@configure.utility(provides=IMCPAuthPolicy)
@implementer(IMCPAuthPolicy)
class OAuthMCPAuthPolicy:
    def is_enabled(self, request, context):
        app = getattr(getattr(request, "application", None), "app", None)
        settings = getattr(app, "settings", None) or app_settings
        applications = set(settings.get("applications") or [])
        return "guillotina.contrib.oauth" in applications and "guillotina.contrib.mcp" in applications

    def unauthorized_headers(self, request, context):
        authz = request.headers.get("AUTHORIZATION", "") or request.headers.get("Authorization", "")
        if authz.lower().startswith("bearer "):
            return self.forbidden_headers(request, context)
        return self._challenge_headers(request, context)

    def forbidden_headers(self, request, context):
        return self._challenge_headers(
            request,
            context,
            error="invalid_token",
            error_description="OAuth access token is not valid for this protected resource",
        )

    def _challenge_headers(self, request, context, *, error=None, error_description=None):
        metadata = well_known_protected_resource_url(request, context)
        parts = [
            'Bearer realm="guillotina-mcp"',
            f'resource_metadata="{metadata}"',
            f'scope="{OAUTH_DEFAULT_SCOPE}"',
        ]
        if error:
            parts.append(f'error="{error}"')
        if error_description:
            parts.append(f'error_description="{error_description}"')
        return {"WWW-Authenticate": ", ".join(parts)}

    def is_authorized(self, request, context):
        oauth = getattr(request, "oauth", None)
        if oauth is None:
            return True
        return mcp_resource(request, context) in oauth.get("resources", set())
