"""OAuth 2.0 Authorization Server Metadata (RFC 8414)."""

from guillotina.contrib.oauth.discovery.routing import register_well_known_handler
from guillotina.contrib.oauth.flow.scopes import oauth_scopes_supported
from guillotina.contrib.oauth.utils.urls import container_issuer_url


def _authorization_server_metadata(request, container):
    issuer = container_issuer_url(request, container)
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "registration_endpoint": f"{issuer}/oauth/register",
        "revocation_endpoint": f"{issuer}/oauth/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "revocation_endpoint_auth_methods_supported": ["none"],
        "resource_indicators_supported": True,
        "authorization_response_iss_parameter_supported": True,
        "scopes_supported": oauth_scopes_supported(),
    }


register_well_known_handler("oauth-authorization-server", _authorization_server_metadata)
