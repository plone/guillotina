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
        "scopes_supported": [
            "guillotina:mcp.read",
            "guillotina:mcp.search",
            "guillotina:mcp.content.read",
        ],
    },
    "check_writable_request": "guillotina.contrib.oauth.utils.check_writable_request",
    "auth_token_validators": [
        "guillotina.contrib.oauth.validators.OAuthJWTValidator",
        "guillotina.auth.validators.SaltedHashPasswordValidator",
        "guillotina.auth.validators.JWTValidator",
    ],
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.oauth.install")
    configure.scan("guillotina.contrib.oauth.permissions")
    configure.scan("guillotina.contrib.oauth.services")
