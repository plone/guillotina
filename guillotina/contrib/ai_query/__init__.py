from guillotina import configure


configure.permission("guillotina.ai_query.Query", "Query data using natural language")
configure.grant(permission="guillotina.ai_query.Query", role="guillotina.Authenticated")


app_settings = {
    "ai_query": {
        "enabled": True,
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_key": None,
        "base_url": None,
        "max_tokens": 500,
        "query_translation_max_tokens": 1024,
        "temperature": 0.1,
        "response_temperature": 0.7,
        "timeout": 30,
        "enable_conversation": True,
        "max_conversation_history": 10,
        "litellm_settings": {
            "retry": {"attempts": 3},
        },
    }
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.ai_query.services")
