from guillotina.contrib.oauth.flow.clients import (
    build_client_from_registration,
    redirect_uri_registered_for_client,
)
from guillotina.contrib.oauth.flow.consent import build_consent_key
from guillotina.contrib.oauth.flow.resources import (
    ensure_default_oauth_resources_registered,
    oauth_allowed_resources,
    oauth_required_audience,
    register_oauth_audience_resolver,
    register_oauth_resource_resolver,
    validate_resource,
)
from guillotina.contrib.oauth.flow.scopes import OAUTH_DEFAULT_SCOPE, oauth_scopes_supported


__all__ = [
    "build_client_from_registration",
    "redirect_uri_registered_for_client",
    "build_consent_key",
    "ensure_default_oauth_resources_registered",
    "oauth_allowed_resources",
    "oauth_required_audience",
    "register_oauth_audience_resolver",
    "register_oauth_resource_resolver",
    "validate_resource",
    "OAUTH_DEFAULT_SCOPE",
    "oauth_scopes_supported",
]
