"""MCP required indicator resolver and auth policy (access phase)."""

from zope.interface import implementer

from guillotina import app_settings, configure
from guillotina.contrib.mcp.interfaces import IMCPAuthPolicy
from guillotina.contrib.oauth.discovery.urls import well_known_protected_resource_url
from guillotina.contrib.oauth.flow.scopes import OAUTH_DEFAULT_SCOPE
from guillotina.contrib.oauth.integrations.mcp.identifiers import mcp_resource_indicator


def _mcp_protocol_audience_resolver(request, container):
    if str(getattr(request, "path", "") or "").endswith("/@mcp/protocol"):
        return mcp_resource_indicator(request, container)


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
        return mcp_resource_indicator(request, context) in oauth.resource_indicators
