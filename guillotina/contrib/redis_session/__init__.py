from guillotina import configure

app_settings = {
    "applications": ["guillotina.contrib.redis"],
    "load_utilities": {
        "session_manager": {
            "provides": "guillotina.interfaces.ISessionManagerUtility",
            "factory": "guillotina.contrib.redis_session.utility.RedisSessionManagerUtility",
        }
    },
    "auth_token_validators": [
        "guillotina.auth.validators.JWTSessionValidator",
    ]
}


def includeme(root, settings):
    pass