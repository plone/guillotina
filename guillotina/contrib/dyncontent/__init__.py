from typing import Any, Dict

from guillotina import configure


app_settings: Dict[str, Any] = {}


def includeme(root, settings):
    configure.scan("guillotina.contrib.dyncontent.vocabularies")
    configure.scan("guillotina.contrib.dyncontent.subscriber")
