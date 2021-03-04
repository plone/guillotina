from guillotina import configure


def includeme(root, settings):
    configure.scan("guillotina.contrib.catalog.pg.parser")
    configure.scan("guillotina.contrib.catalog.pg.utility")
