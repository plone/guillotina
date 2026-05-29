from guillotina import app_settings


OAUTH_DEFAULT_SCOPE = "guillotina:access"
OAUTH_SCOPES_SUPPORTED = (OAUTH_DEFAULT_SCOPE,)
OAUTH_SCOPE_DESCRIPTIONS = {
    OAUTH_DEFAULT_SCOPE: "Access Guillotina on behalf of the authenticated user.",
}


def oauth_scopes_supported():
    configured = app_settings.get("oauth", {}).get("scopes_supported")
    if configured is None:
        return list(OAUTH_SCOPES_SUPPORTED)
    return list(configured)
