DEFAULT_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.redis_session"],
    "auth_token_validators": [
        "guillotina.auth.validators.JWTSessionValidator",
        "guillotina.auth.validators.SaltedHashPasswordValidator",
    ],
}
