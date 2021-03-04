from guillotina import configure

import logging


logger = logging.getLogger("guillotina")

app_settings = {
    "load_utilities": {
        "catalog": {
            "provides": "guillotina.interfaces.ICatalogUtility",
            "factory": "guillotina.contrib.catalog.pg.utility.PGSearchUtility",
        }
    }
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.catalog.pg.parser")
    configure.scan("guillotina.contrib.catalog.pg.utility")
