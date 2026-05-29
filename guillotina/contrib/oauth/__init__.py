from guillotina import configure


app_settings = {
    "oauth": {
        "enabled": True,
        "issuer": None,
        "authorization_code_ttl": 600,
        "access_token_ttl": 3600,
        "refresh_token_ttl": 2592000,
        "require_pkce": True,
        "allowed_code_challenge_methods": ["S256"],
        "scopes_supported": ["guillotina:access"],
    },
    "check_writable_request": "guillotina.contrib.oauth.api.request.check_writable_request",
    "auth_token_validators": [
        "guillotina.contrib.oauth.auth.validators.OAuthJWTValidator",
        "guillotina.auth.validators.SaltedHashPasswordValidator",
        "guillotina.auth.validators.JWTValidator",
    ],
    "load_utilities": {
        "oauth_storage": {
            "provides": "guillotina.contrib.oauth.interfaces.IOAuthStorageUtility",
            "factory": "guillotina.contrib.oauth.storage.utility.OAuthStorageUtility",
            "settings": {
                "cleanup_interval": 900,
                "cleanup_batch_size": 5000,
            },
        }
    },
}


def includeme(root, settings):
    from guillotina.contrib.oauth.flow.resources import ensure_default_oauth_resources_registered

    ensure_default_oauth_resources_registered()
    configure.scan("guillotina.contrib.oauth.install")
    configure.scan("guillotina.contrib.oauth.api.services")
    if "guillotina.contrib.mcp" in set(settings.get("applications") or []):
        configure.scan("guillotina.contrib.oauth.integrations.mcp")
