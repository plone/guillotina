from guillotina import configure


app_settings = {
    "oauth": {
        "enabled": True,
        "issuer": None,
        # When False (default) the issuer is derived only from the transport
        # scheme and Host header. Enable behind a trusted reverse proxy so that
        # X-Forwarded-Proto / X-VirtualHost-* headers are honored.
        "trust_proxy_headers": False,
        "authorization_code_ttl": 600,
        "access_token_ttl": 3600,
        "refresh_token_ttl": 2592000,
        "allowed_code_challenge_methods": ["S256"],
        "scopes_supported": ["guillotina:access"],
        # Dynamic client registration throttling (per client IP, sliding window).
        # Set ``registration_rate_limit`` to 0 to disable.
        "registration_rate_limit": 20,
        "registration_rate_window": 600,
        # Failed-login throttling at the authorization endpoint (per client IP +
        # username, sliding window). Set ``login_rate_limit`` to 0 to disable.
        "login_rate_limit": 10,
        "login_rate_window": 300,
        # Token and revocation endpoint throttling (per client IP).
        # Set the limit to 0 to disable.
        "token_rate_limit": 120,
        "token_rate_window": 60,
        "revoke_rate_limit": 120,
        "revoke_rate_window": 60,
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
