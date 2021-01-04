from guillotina import configure
from typing import Dict, Any


app_settings : Dict[str, Any] = {}


def includeme(root, settings):
    configure.scan("guillotina.contrib.dyncontent.vocabularies")
    configure.scan("guillotina.contrib.dyncontent.subscriber")
