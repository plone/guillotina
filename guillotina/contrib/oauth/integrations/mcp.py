from zope.interface import implementer

from guillotina import app_settings, configure
from guillotina.contrib.mcp.interfaces import IMCPAuthPolicy
from guillotina.contrib.oauth.api.services import register_well_known_handler
from guillotina.contrib.oauth.api.urls import container_url, well_known_protected_resource_url
from guillotina.contrib.oauth.flow.resources import (
    register_oauth_audience_resolver,
    register_oauth_resource_resolver,
)
from guillotina.contrib.oauth.flow.scopes import OAUTH_DEFAULT_SCOPE, oauth_scopes_supported


def mcp_resource(request, container):
    return f"{container_url(request, container)}/@mcp/protocol"


def _mcp_protocol_resource_resolver(request, container):
    return {mcp_resource(request, container)}


def _mcp_protocol_audience_resolver(request, container):
    if str(getattr(request, "path", "") or "").endswith("/@mcp/protocol"):
        return mcp_resource(request, container)


_mcp_protocol_resource_resolver._oauth_resource_source = "mcp"
_mcp_protocol_audience_resolver._oauth_resource_source = "mcp"
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
