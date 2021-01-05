from guillotina import configure
from typing import Any
from typing import Dict


app_settings: Dict[str, Any] = {}


def includeme(root, settings):
    configure.scan("guillotina.contrib.dyncontent.vocabularies")
    configure.scan("guillotina.contrib.dyncontent.subscriber")
