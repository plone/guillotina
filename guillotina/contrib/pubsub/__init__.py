app_settings = {
    "load_utilities": {
        "guillotina_pubsub": {
            "provides": "guillotina.interfaces.IPubSubUtility",
            "factory": "guillotina.contrib.pubsub.utility.PubSubUtility",
            "settings": {"driver": "guillotina.contrib.redis"},
        }
    }
}


def includeme(root, settings):
    pass
