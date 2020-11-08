from guillotina import configure


def includeme(root, settings):
    configure.scan("guillotina.contrib.vocabularies.countries")
    configure.scan("guillotina.contrib.vocabularies.languages")
